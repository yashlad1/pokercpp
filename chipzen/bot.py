"""pokercpp on Chipzen.

The strategy lives in C++ — the Monte Carlo equity engine this repo is built
around, compiled into the `pokercpp_engine` extension module. This file is
the wire adapter: it owns the WebSocket and guarantees that whatever the
engine returns is a legal action the server actually offered.

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
STATE_LOG_LIMIT = 50  # raw GameState lines logged after each match start

# 5000 trials puts the 95% interval near +/-1.4% and costs ~12 ms, against a
# 2000 ms ranked budget. Accuracy is nowhere near the binding constraint.
SIMS = int(os.environ.get("POKERCPP_SIMS", "5000"))


def _hist(state: GameState) -> str:
    """seat:action:amount per entry; the log line runs outside the try."""
    try:
        return ",".join(
            f"{e.get('seat')}:{e.get('action')}:{e.get('amount')}"
            for e in (state.action_history or ())
        ) or "-"
    except Exception:
        return "?"


def _villain_raises(state: GameState) -> int:
    """Count aggressive actions by anyone other than us in this hand.

    This is the whole opponent model: how many times they have chosen to put
    money in voluntarily. Posting a blind is not a choice, so the synthetic
    entries are skipped.
    """
    n = 0
    for entry in state.action_history or ():
        if entry.get("seat") == state.your_seat:
            continue
        if entry.get("action") in ("raise", "bet", "all_in"):
            n += 1
    return n


def _current_blinds(state: GameState) -> tuple[int, int]:
    """Read this hand's blinds off the synthetic entries in action_history.

    Blinds escalate, so caching them at match start would leave every
    stack-in-BB calculation drifting as the structure climbs.
    """
    sb = bb = 0
    for entry in state.action_history or ():
        action = entry.get("action")
        if action == "post_small_blind":
            sb = int(entry.get("amount") or 0)
        elif action == "post_big_blind":
            bb = int(entry.get("amount") or 0)
        elif action != "post_ante":
            break  # past the synthetic entries
    return sb, bb


def _raise_band(state: GameState, valid) -> tuple[int, int]:
    """The (lo, hi) raise bounds, for the engine and for _to_action alike.

    A stack too short for a full raise is offered as "raise" with min_raise
    above max_raise (max_raise is the whole stack): the only legal amount is
    max_raise, so the band collapses to it.
    """
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
        self.last_bb = int(cfg.get("big_blind") or 0)  # fallback until a hand shows its own
        self.hand_bb: dict[int, int] = {}
        self._fixed_bb = None  # bb fixed for the current hand
        self._last_n = 0  # last nonzero hand_number seen

    def on_match_start(self, match_info):
        # One process can play several matches; do not carry one opponent into the next.
        self.opponent = Opponent()
        self._reset_blinds(match_info)
        self._state_logs = 0
        self._round_seen, self._round_seq = False, 0
        try:
            seats = (match_info or {}).get("seats") or []
            logger.info(
                "match_start seats=%s",
                [(s.get("seat"), s.get("is_self")) for s in seats if isinstance(s, dict)],
            )
        except Exception:
            logger.exception("match_start log failed")

    def on_round_start(self, message):
        self._round_seen = True
        self._round_seq += 1
        self._fixed_bb = None  # a new hand: its bb is not fixed yet
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
        except Exception:
            logger.exception("round_result log failed")
        self._turns = 0

    def _bb(self, state: GameState) -> int:
        """This hand's big blind, from the first of these that applies:

        1. the bb already fixed for this hand;
        2. the history's post_big_blind amount;
        3. a value backed out of pot and to_call, on our first preflop
           decision of the hand only (later, pot and to_call include raises:
           a 3-bet read as 'pot + to_call' is the 3-bet size, not the bb).
           Heads-up the button posts the small blind, so pot + to_call (as
           SB) or pot - to_call (as BB) is two big blinds, antes removed;
        4. last_bb, which starts as the game_config big blind.

        A hand starts at on_round_start or when a nonzero hand_number
        changes. Cross-check against min_raise is logged, never applied.
        """
        n = state.hand_number
        if n and n != self._last_n:
            self._last_n, self._fixed_bb = n, None
        if n and n in self.hand_bb:
            return self.hand_bb[n]
        preflop = state.phase == "preflop"
        first = preflop and not any(
            e.get("seat") == state.your_seat and not str(e.get("action", "")).startswith("post_")
            for e in state.action_history or ())
        # With no hand_number and no round_start there is no hand boundary to
        # trust, so a fixed bb is reused only after our first preflop decision.
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
                # Only a shove is offered: let the engine pick it.
                lo = hi = int(state.your_stack or 0)
            else:
                lo = hi = 0
            self.opponent.saw(state.hand_number or self._round_seq, vr)
            d = pokercpp_engine.decide(
                # Card.__str__ is already the wire's two-char form.
                hole=[str(c) for c in (state.hole_cards or ())],
                board=[str(c) for c in (state.board or ())],
                pot=int(state.pot or 0),
                to_call=int(state.to_call or 0),
                # The SDK passes the server's bounds through; 0 means raising is closed.
                min_raise=lo, max_raise=hi,
                stack=int(state.your_stack or 0),
                bb=int(bb or 0),
                sims=SIMS,
                villain_raises=vr,
                range_floor=self.opponent.range_floor(vr),
            )
            action = self._to_action(d, state, valid)
        except Exception:
            # decide() must never raise: an exception here costs the whole
            # match, while a safe default costs one pot.
            # A traceback here is the signal that the engine never ran and
            # every decision this match is a fallback, not a strategy.
            logger.exception("ENGINE FAILED - falling back to check/fold")
            d = None
            bb = 0
            action = self._safe_default(valid)

        logger.info(
            "hand=%s phase=%s pot=%s to_call=%s bb=%s min_raise=%s max_raise=%s "
            "stack=%s seat=%s dealer=%s opp=%s hist=%s hole=%s legal=%s "
            "range=%s equity=%s realized=%s required=%s -> %s%s",
            state.hand_number, state.phase, state.pot, state.to_call,
            bb, getattr(state, "min_raise", None), getattr(state, "max_raise", None),
            getattr(state, "your_stack", None), getattr(state, "your_seat", None),
            getattr(state, "dealer_seat", None), getattr(state, "opponent_stacks", None),
            _hist(state),
            "".join(str(c) for c in (state.hole_cards or ())) or "NONE",
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
    def _safe_default(valid: list[str]) -> Action:
        if "check" in valid:
            return Action.check()
        return Action.fold()

    def _to_action(self, d: dict, state: GameState, valid: list[str]) -> Action:
        """Map the engine's reply onto a legal action.

        Every branch re-checks ``valid_actions``: the engine reasons about
        equity and knows nothing about which actions the server offered this
        turn, so this is the only place legality is enforced.
        """
        if not d:
            return self._safe_default(valid)

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
            return Action.call() if "call" in valid else self._safe_default(valid)

        if word == "check":
            return self._safe_default(valid)

        if word == "fold":
            # Folding for free is strictly worse than checking.
            if state.to_call == 0 and "check" in valid:
                return Action.check()
            return Action.fold() if "fold" in valid else self._safe_default(valid)

        return self._safe_default(valid)


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
