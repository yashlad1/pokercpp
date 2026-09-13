"""pokercpp on Chipzen.

The strategy lives in solver.cpp — the Monte Carlo equity engine this repo
is built around. This file is the wire adapter: it owns the WebSocket, keeps
one long-lived solver process, and guarantees that whatever comes back is a
legal action the server offered.

Environment:
    CHIPZEN_WS_URL      WebSocket URL injected by the platform.
    CHIPZEN_TOKEN       Bot API token.
    CHIPZEN_TICKET      Single-use ticket alternative.
    POKERCPP_SIMS       Monte Carlo trials per decision (default 5000).
    POKERCPP_SOLVER     Path to the solver binary (default /bot/solver).
"""

from __future__ import annotations

import asyncio
import logging
import os
import select
import subprocess
import sys

from chipzen import Action, Bot, GameState
from chipzen.client import run_bot

logger = logging.getLogger("pokercpp")

SOLVER = os.environ.get("POKERCPP_SOLVER", "/bot/solver")
SIMS = int(os.environ.get("POKERCPP_SIMS", "5000"))

# The ranked bot-vs-bot budget is 2000 ms end to end. The solver answers in
# ~30 ms at 5000 trials, so this cutoff only ever fires if it has wedged or
# died; it exists so a wedged solver costs one fallback instead of the match.
SOLVER_TIMEOUT_S = 1.0


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
        elif action not in ("post_ante",):
            break  # past the synthetic entries
    return sb, bb


class PokerCppBot(Bot):
    def __init__(self) -> None:
        super().__init__()
        self._proc: subprocess.Popen | None = None

    # ----- solver process --------------------------------------------------

    def _solver(self) -> subprocess.Popen | None:
        """Return a live solver, starting one if needed.

        Started lazily on first use rather than at import: the executor gives
        the container ~15 s to attach, and spending any of it here is wasted.
        """
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        try:
            self._proc = subprocess.Popen(
                [SOLVER],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            logger.info("solver started pid=%s sims=%d", self._proc.pid, SIMS)
        except OSError:
            logger.exception("solver failed to start")
            self._proc = None
        return self._proc

    def _ask(self, line: str) -> str | None:
        proc = self._solver()
        if proc is None or proc.stdin is None or proc.stdout is None:
            return None
        try:
            proc.stdin.write(line + "\n")
            proc.stdin.flush()
            ready, _, _ = select.select([proc.stdout], [], [], SOLVER_TIMEOUT_S)
            if not ready:
                # Wedged. Kill it so the next decision starts a fresh one
                # rather than reading this hand's answer next hand.
                logger.warning("solver timed out; restarting")
                proc.kill()
                self._proc = None
                return None
            return (proc.stdout.readline() or "").strip()
        except (BrokenPipeError, OSError):
            logger.warning("solver pipe broke; restarting")
            self._proc = None
            return None

    # ----- decision --------------------------------------------------------

    def decide(self, state: GameState) -> Action:
        valid = list(state.valid_actions or ())
        try:
            reply = self._ask(self._encode(state))
            action = self._to_action(reply, state, valid)
        except Exception:
            # decide() must never raise: an exception here costs the whole
            # match, while a safe default costs one pot.
            logger.exception("decide failed; using safe default")
            action = self._safe_default(valid)

        logger.info(
            "hand=%s phase=%s to_call=%s legal=%s -> %s",
            state.hand_number, state.phase, state.to_call,
            ",".join(valid) or "-", action.action,
        )
        return action

    def _encode(self, state: GameState) -> str:
        _, bb = _current_blinds(state)
        # Card.__str__ is already the wire's two-char form.
        hole = [str(c) for c in (state.hole_cards or ())]
        board = [str(c) for c in (state.board or ())]
        parts = [
            str(len(hole)), *hole,
            str(len(board)), *board,
            str(int(state.pot or 0)),
            str(int(state.to_call or 0)),
            str(int(state.min_raise or 0)),
            str(int(state.max_raise or 0)),
            str(int(state.your_stack or 0)),
            str(int(bb or 0)),
            str(SIMS),
        ]
        return " ".join(parts)

    @staticmethod
    def _safe_default(valid: list[str]) -> Action:
        if "check" in valid:
            return Action.check()
        return Action.fold()

    def _to_action(self, reply: str | None, state: GameState, valid: list[str]) -> Action:
        """Map the solver's reply onto a legal action.

        Every branch re-checks ``valid_actions``: the solver reasons about
        equity and knows nothing about which actions the server offered this
        turn, so this is the only place legality is enforced.
        """
        if not reply:
            return self._safe_default(valid)

        word, _, amount = reply.partition(" ")

        if word == "raise" and "raise" in valid:
            try:
                target = int(amount)
            except ValueError:
                target = 0
            lo, hi = int(state.min_raise or 0), int(state.max_raise or 0)
            if lo > 0 and hi > 0:
                target = max(lo, min(target, hi))
                return Action.raise_to(target)
            # Raising was illegal after all — fall through to the next best.
            word = "call" if state.to_call else "check"

        if word == "call":
            if "call" in valid:
                return Action.call()
            return self._safe_default(valid)

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

    token = os.environ.get("CHIPZEN_TOKEN")
    ticket = os.environ.get("CHIPZEN_TICKET")
    await run_bot(
        ws_url,
        PokerCppBot(),
        token=token if token is not None else None,
        ticket=ticket if ticket else None,
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
