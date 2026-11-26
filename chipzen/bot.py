"""pokercpp on Chipzen: the wire adapter around the `pokercpp_engine` extension.

The engine is linked in rather than shelled out to because the platform
sandbox blocks both `subprocess` and `ctypes`.

Environment:
    CHIPZEN_WS_URL      WebSocket URL injected by the platform.
    CHIPZEN_TOKEN       Bot API token.
    CHIPZEN_TICKET      Single-use ticket alternative.
    POKERCPP_SIMS       Monte Carlo trials per decision (default 5000).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import os
import sys

from chipzen import Action, Bot, GameState
from chipzen.client import run_bot

import pokercpp_engine
from opponent import Opponent

logger = logging.getLogger("pokercpp")

VERSION = "4.0.1"
STATE_LOG_LIMIT = 50

# 5000 trials: 95% interval near +/-1.4%, ~12 ms of a 2000 ms ranked budget.
try:
    SIMS = int(os.environ.get("POKERCPP_SIMS", "5000"))
except ValueError:
    SIMS = 5000


def _hist(state: GameState) -> str:
    try:
        return ",".join(
            f"{e.get('seat')}:{e.get('action')}:{e.get('amount')}"
            for e in (state.action_history or ())
        ) or "-"
    except Exception:
        return "?"


def _villain_raises(state: GameState) -> int:
    # Posting a blind is not a choice, so the synthetic blind entries are skipped.
    n = 0
    for entry in state.action_history or ():
        if entry.get("seat") == state.your_seat:
            continue
        if entry.get("action") in ("raise", "bet", "all_in"):
            n += 1
    return n


def _villain_calls(state: GameState) -> int:
    # An opponent call that matches an earlier bet or raise this hand; a limp, blinds and checks do not count.
    n, bet = 0, False
    for entry in state.action_history or ():
        action = entry.get("action")
        if action in ("raise", "bet", "all_in"):
            bet = True
        elif action == "call" and bet and entry.get("seat") != state.your_seat:
            n += 1
    return n


def _current_blinds(state: GameState) -> tuple[int, int]:
    # Blinds escalate, so read them each hand, not once at match start.
    sb = bb = 0
    for entry in state.action_history or ():
        action = entry.get("action")
        if action == "post_small_blind":
            sb = int(entry.get("amount") or 0)
        elif action == "post_big_blind":
            bb = int(entry.get("amount") or 0)
        elif action != "post_ante":
            break
    return sb, bb


def _raise_band(state: GameState, valid) -> tuple[int, int]:
    """The server offers a short stack "raise" with min_raise above max_raise; only max_raise is legal."""
    lo, hi = int(state.min_raise or 0), int(state.max_raise or 0)
    if "raise" in valid and 0 < hi < lo:
        lo = hi
    return lo, hi


class PokerCppBot(Bot):
    def __init__(self):
        super().__init__()
        self.opponent = Opponent()
        self._reset_blinds({})
        self._turns = 0
        self._state_logs = 0
        self._round_seen, self._round_seq = False, 0

    def _reset_blinds(self, match_info):
        cfg = (match_info or {}).get("game_config") or {}
        self.ante = int(cfg.get("ante") or 0)
        self.last_bb = int(cfg.get("big_blind") or 0)
        self.hand_bb: dict[int, int] = {}
        self._fixed_bb = None
        self._last_n = 0

    def on_match_start(self, match_info):
        self.opponent = Opponent()
        self._reset_blinds(match_info)
        self._state_logs = 0
        self._round_seen, self._round_seq = False, 0
        try:
            logger.info("pokercpp v%s commit=%s", VERSION, os.environ.get("POKERCPP_COMMIT", "unknown"))
            seats = (match_info or {}).get("seats") or []
            logger.info(
                "match_start seats=%s",
                [(s.get("seat"), s.get("is_self"), s.get("display_name"), s.get("participant_id"))
                 for s in seats if isinstance(s, dict)],
            )
        except Exception:
            logger.exception("match_start log failed")

    def on_round_start(self, message):
        self._round_seen = True
        self._round_seq += 1
        self._fixed_bb = None
        super().on_round_start(message)

    def on_turn_result(self, message):
        self._turns += 1

    def on_round_result(self, message):
        try:
            res = (message or {}).get("result") or {}
            hist = res.get("action_history") or []
            entries = ",".join(
                f"{e.get('seat')}:{e.get('action')}:{e.get('amount')}:{e.get('phase')}"
                for e in hist
                if isinstance(e, dict)
            )
            logger.info(
                "round_result hand=%s history_len=%s turn_results=%s showdown=%s winners=%s history=%s",
                res.get("hand_number"),
                len(hist),
                self._turns,
                len(res.get("showdown") or []),
                res.get("winner_seats"),
                entries,
            )
            logger.info("ROUND %s", json.dumps({k: v for k, v in res.items() if k != "action_history"}, default=str))
        except Exception:
            logger.exception("round_result log failed")
        self._turns = 0

    def _bb(self, state: GameState) -> int:
        # Precedence: the bb fixed for this hand, the history's post_big_blind, a value backed out of pot and
        # to_call on our first preflop decision only (heads-up that sum is 2 bb, antes removed), then last_bb.
        # A hand starts at on_round_start or when a nonzero hand_number changes.
        n = state.hand_number
        if n and n != self._last_n:
            self._last_n, self._fixed_bb = n, None
        if n and n in self.hand_bb:
            return self.hand_bb[n]
        preflop = state.phase == "preflop"
        first = preflop and not any(
            e.get("seat") == state.your_seat and not str(e.get("action", "")).startswith("post_")
            for e in state.action_history or ())
        if self._fixed_bb and (n or self._round_seen or not first):
            return self._fixed_bb
        hist_bb = _current_blinds(state)[1]
        pot, to_call = int(state.pot or 0) - 2 * self.ante, int(state.to_call or 0)
        derived = None
        if first and state.dealer_seat is not None:
            sb_seat = state.your_seat == state.dealer_seat
            derived = (pot + to_call if sb_seat else pot - to_call) // 2
        bb = hist_bb or derived or 0
        if not hist_bb and first and state.dealer_seat is None:
            logger.warning("dealer_seat missing: cannot derive bb, using last_bb=%s", self.last_bb)
        if first and "raise" in (state.valid_actions or ()):
            lo, hi = int(state.min_raise or 0), int(state.max_raise or 0)
            ref = bb if bb > 0 else self.last_bb
            if 0 < lo < hi and to_call < ref and lo != 2 * ref:
                logger.warning(
                    "BB MISMATCH bb=%s derived=%s history=%s min_raise=%s pot=%s to_call=%s "
                    "seat=%s dealer=%s last_bb=%s",
                    ref, derived, hist_bb, lo, state.pot, state.to_call,
                    state.your_seat, state.dealer_seat, self.last_bb)
        if bb > 0:
            if n:
                self.hand_bb[n] = bb
            self._fixed_bb = self.last_bb = bb
            return bb
        return max(self.last_bb, 0)

    def _log_state(self, state: GameState) -> None:
        if self._state_logs >= STATE_LOG_LIMIT:
            return
        self._state_logs += 1
        try:
            raw = {f.name: getattr(state, f.name, None) for f in dataclasses.fields(state)}
            logger.info("STATE %s", json.dumps(raw, default=str))
        except Exception:
            logger.exception("state log failed")

    def decide(self, state: GameState) -> Action:
        self._log_state(state)
        valid = list(state.valid_actions or ())
        try:
            bb = self._bb(state)
            vr = _villain_raises(state)
            if "raise" in valid:
                lo, hi = _raise_band(state, valid)
            elif "all_in" in valid:
                lo = hi = int(state.your_stack or 0)
            else:
                lo = hi = 0
            self.opponent.saw(state.hand_number or self._round_seq, vr)
            d = pokercpp_engine.decide(
                hole=[str(c) for c in (state.hole_cards or ())],
                board=[str(c) for c in (state.board or ())],
                pot=int(state.pot or 0),
                to_call=int(state.to_call or 0),
                # 0 means raising is closed.
                min_raise=lo, max_raise=hi,
                stack=int(state.your_stack or 0),
                bb=int(bb or 0),
                sims=SIMS,
                villain_raises=vr,
                villain_calls=_villain_calls(state),
                range_floor=self.opponent.range_floor(vr),
            )
            action = self._to_action(d, state, valid)
        except Exception:
            # decide() must never raise: an exception costs the match, a safe default one pot.
            logger.exception("ENGINE FAILED - falling back to check/fold")
            d = None
            bb = 0
            action = self._safe_default(state, valid)

        logger.info(
            "hand=%s phase=%s pot=%s to_call=%s bb=%s min_raise=%s max_raise=%s "
            "stack=%s seat=%s dealer=%s opp=%s hist=%s hole=%s board=%s legal=%s "
            "range=%s equity=%s realized=%s required=%s -> %s%s",
            state.hand_number, state.phase, state.pot, state.to_call,
            bb, getattr(state, "min_raise", None), getattr(state, "max_raise", None),
            getattr(state, "your_stack", None), getattr(state, "your_seat", None),
            getattr(state, "dealer_seat", None), getattr(state, "opponent_stacks", None),
            _hist(state),
            "".join(str(c) for c in (state.hole_cards or ())) or "NONE",
            "".join(str(c) for c in (state.board or ())) or "-",
            ",".join(valid) or "-",
            f"{d['range']:.2f}" if d else "n/a",
            f"{d['equity']:.3f}" if d else "n/a",
            f"{d['realized']:.3f}" if d else "n/a",
            f"{d['required']:.3f}" if d else "n/a",
            action.action,
            f" {action.amount}" if action.action == "raise" else "",
        )
        return action

    @staticmethod
    def _safe_default(state: GameState, valid: list[str]) -> Action:
        for name, make in (("check", Action.check), ("fold", Action.fold),
                           ("call", Action.call), ("all_in", Action.all_in)):
            if name in valid:
                return make()
        if "raise" in valid:
            lo, _ = _raise_band(state, valid)
            if lo > 0:
                return Action.raise_to(lo)
        return Action.fold()

    def _to_action(self, d: dict, state: GameState, valid: list[str]) -> Action:
        # The engine knows nothing of the actions offered this turn, so every branch re-checks valid_actions.
        if not d:
            return self._safe_default(state, valid)

        word = d["action"]

        if word == "raise" and "raise" not in valid and "all_in" in valid:
            return Action.all_in()

        if word == "raise" and "raise" in valid:
            target = int(d["amount"])
            lo, hi = _raise_band(state, valid)
            if lo > 0 and hi > 0:
                target = max(lo, min(target, hi))
                if target >= hi and "all_in" in valid:
                    return Action.all_in()
                return Action.raise_to(target)
            # Raising was illegal after all — fall through to the next best.
            word = "call" if state.to_call else "check"

        if word == "call" and "call" not in valid and "all_in" in valid:
            return Action.all_in()  # facing a bet >= stack: the call is offered as all_in

        if word == "call":
            return Action.call() if "call" in valid else self._safe_default(state, valid)

        if word == "fold":
            if state.to_call == 0 and "check" in valid:
                return Action.check()
            return Action.fold() if "fold" in valid else self._safe_default(state, valid)

        return self._safe_default(state, valid)


async def _amain() -> None:
    logging.basicConfig(
        level=os.environ.get("POKERCPP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("pokercpp v%s commit=%s", VERSION, os.environ.get("POKERCPP_COMMIT", "unknown"))
    ws_url = os.environ.get("CHIPZEN_WS_URL") or os.environ.get("CHIPZEN_URL", "")
    if not ws_url:
        logger.error("CHIPZEN_WS_URL is required")
        sys.exit(2)

    await run_bot(
        ws_url,
        PokerCppBot(),
        token=os.environ.get("CHIPZEN_TOKEN"),
        ticket=os.environ.get("CHIPZEN_TICKET") or None,
        client_name="pokercpp",
        client_version=VERSION,
    )


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        logger.info("interrupted; exiting")


if __name__ == "__main__":
    main()
