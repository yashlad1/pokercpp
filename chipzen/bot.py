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
import logging
import os
import sys

from chipzen import Action, Bot, GameState
from chipzen.client import run_bot

import pokercpp_engine

logger = logging.getLogger("pokercpp")

# 5000 trials puts the 95% interval near +/-1.4% and costs ~12 ms, against a
# 2000 ms ranked budget. Accuracy is nowhere near the binding constraint.
SIMS = int(os.environ.get("POKERCPP_SIMS", "5000"))


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


class PokerCppBot(Bot):
    def decide(self, state: GameState) -> Action:
        valid = list(state.valid_actions or ())
        try:
            _, bb = _current_blinds(state)
            d = pokercpp_engine.decide(
                # Card.__str__ is already the wire's two-char form.
                hole=[str(c) for c in (state.hole_cards or ())],
                board=[str(c) for c in (state.board or ())],
                pot=int(state.pot or 0),
                to_call=int(state.to_call or 0),
                min_raise=int(state.min_raise or 0),
                max_raise=int(state.max_raise or 0),
                stack=int(state.your_stack or 0),
                bb=int(bb or 0),
                sims=SIMS,
                villain_raises=_villain_raises(state),
            )
            action = self._to_action(d, state, valid)
        except Exception:
            # decide() must never raise: an exception here costs the whole
            # match, while a safe default costs one pot.
            # A traceback here is the signal that the engine never ran and
            # every decision this match is a fallback, not a strategy.
            logger.exception("ENGINE FAILED - falling back to check/fold")
            d = None
            action = self._safe_default(valid)

        logger.info(
            "hand=%s phase=%s pot=%s to_call=%s hole=%s legal=%s "
            "range=%s equity=%s realized=%s required=%s -> %s%s",
            state.hand_number, state.phase, state.pot, state.to_call,
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

        if word == "raise" and "raise" in valid:
            target = int(d["amount"])
            lo, hi = int(state.min_raise or 0), int(state.max_raise or 0)
            if lo > 0 and hi > 0:
                return Action.raise_to(max(lo, min(target, hi)))
            # Raising was illegal after all — fall through to the next best.
            word = "call" if state.to_call else "check"

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
        client_version="1.0.0",
    )


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        logger.info("interrupted; exiting")


if __name__ == "__main__":
    main()
