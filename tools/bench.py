"""Offline measurement for the Chipzen bot.

Plays pokercpp against an opponent over many hands and reports the result in
big blinds per 100 hands, with a confidence interval. Exists because the
platform rate-limits challenge matches, and because a win rate needs far more
hands than that allows: at a standard deviation near 100 bb/100, telling a
10 bb/100 edge from zero takes roughly 38,000 hands.

Two things make that sample affordable.

Duplicate dealing. Every deal is played twice, the same cards to the same
seat, with the agents swapped. Each agent therefore holds both sides of every
deal and card luck cancels between the two runs rather than having to be
averaged away. What is left measures the strategies.

pokerkit runs the game. Min-raise sizing after an all-in, uncalled-bet
returns, side pots and showdown ordering are where a hand-rolled engine goes
quietly wrong, and none of it is what this is trying to test.

Usage:
    pip install pokerkit pybind11
    g++ -std=c++17 -O2 -shared -fPIC $(python -m pybind11 --includes) \
        chipzen/pokercpp_engine.cpp montecarlo/MonteCarloSimulator.cpp \
        model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp \
        -o chipzen/pokercpp_engine$(python3-config --extension-suffix)
    PYTHONPATH=chipzen python tools/bench.py --hands 2000 --vs reference
"""

from __future__ import annotations

import argparse
import math
import os
import random
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chipzen"))

import pokercpp_engine
from pokerkit import Automation as A
from pokerkit import NoLimitTexasHoldem

AUTOMATIONS = (
    A.ANTE_POSTING, A.BET_COLLECTION, A.BLIND_OR_STRADDLE_POSTING,
    A.CARD_BURNING, A.HOLE_DEALING, A.BOARD_DEALING,
    A.HOLE_CARDS_SHOWING_OR_MUCKING, A.HAND_KILLING,
    A.CHIPS_PUSHING, A.CHIPS_PULLING,
)

RANK_ORDER = {r: i for i, r in enumerate("23456789TJQKA")}


class View:
    """What an agent sees on its turn. Mirrors the Chipzen GameState fields
    the bot actually reads, so an agent written here and the real bot are
    deciding from the same information."""

    __slots__ = ("hole", "board", "pot", "to_call", "min_raise", "max_raise",
                 "stack", "bb", "villain_raises")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw[k])


# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------

class PokerCpp:
    """The real engine, with its knobs exposed so variants can be compared."""

    def __init__(self, sims=2000, name="pokercpp", realization_scale=1.0,
                 bluff_enabled=True):
        self.sims = sims
        self.name = name
        self.realization_scale = realization_scale
        self.bluff_enabled = bluff_enabled

    def act(self, v: View):
        d = pokercpp_engine.decide(
            hole=v.hole, board=v.board, pot=v.pot, to_call=v.to_call,
            min_raise=v.min_raise, max_raise=v.max_raise, stack=v.stack,
            bb=v.bb, sims=self.sims, villain_raises=v.villain_raises,
            realization_scale=self.realization_scale,
            bluff_enabled=self.bluff_enabled,
        )
        return d["action"], d["amount"]


class Reference:
    """The strategy Chipzen ships as its reference bot: preflop rank buckets,
    postflop made-hand class. Not strong, but it is what a straightforward
    entry looks like, which makes it the honest baseline to beat."""

    name = "reference"

    def act(self, v: View):
        if len(v.board) == 0:
            return self._preflop(v)
        return self._postflop(v)

    @staticmethod
    def _bucket(hole):
        r1, r2 = hole[0][0], hole[1][0]
        suited = hole[0][1] == hole[1][1]
        hi, lo = sorted((r1, r2), key=lambda r: -RANK_ORDER[r])
        if r1 == r2:
            return "premium" if r1 in "JQKA" else ("strong" if r1 in "9T" else "medium")
        if {hi, lo} == {"A", "K"}:
            return "premium"
        if hi == "A" and lo in "QJT":
            return "strong" if suited else "medium"
        if hi == "K" and lo in "QJ":
            return "strong" if suited else "medium"
        if hi in "QJ" and lo in "T9":
            return "strong" if suited else "medium"
        return "medium" if hi == "A" else "weak"

    def _preflop(self, v: View):
        b = self._bucket(v.hole)
        if b == "premium" and v.max_raise:
            return "raise", min(max(v.min_raise * 3, v.min_raise), v.max_raise)
        if b == "strong":
            if v.to_call == 0 and v.max_raise:
                return "raise", min(max(v.min_raise * 2, v.min_raise), v.max_raise)
            return ("call", 0) if v.to_call <= v.stack // 10 else ("fold", 0)
        if b == "medium":
            if v.to_call == 0:
                return "check", 0
            return ("call", 0) if v.to_call <= v.stack // 30 else ("fold", 0)
        return ("check", 0) if v.to_call == 0 else ("fold", 0)

    def _postflop(self, v: View):
        counts = sorted(Counter(c[0] for c in v.hole + v.board).values(), reverse=True)
        klass = 3 if counts[0] >= 3 else (2 if counts[:2] == [2, 2] else (1 if counts[0] == 2 else 0))
        if klass >= 2:
            if v.villain_raises == 0 and v.max_raise:
                return "raise", min(max(int(v.pot * 0.66), v.min_raise), v.max_raise)
            return ("call", 0) if v.to_call else ("check", 0)
        if klass == 1:
            if v.to_call == 0:
                return "check", 0
            return ("call", 0) if v.to_call <= v.pot // 3 else ("fold", 0)
        return ("check", 0) if v.to_call == 0 else ("fold", 0)


class CallingStation:
    """Never folds. A bot that cannot beat this is not bluffing profitably."""
    name = "station"

    def act(self, v: View):
        return ("check", 0) if v.to_call == 0 else ("call", 0)


class Nit:
    """Only continues with premium holdings. A bot that cannot beat this is
    not stealing enough."""
    name = "nit"

    def act(self, v: View):
        r1, r2 = v.hole[0][0], v.hole[1][0]
        strong = r1 == r2 and RANK_ORDER[r1] >= RANK_ORDER["T"]
        strong = strong or (RANK_ORDER[r1] >= RANK_ORDER["Q"] and RANK_ORDER[r2] >= RANK_ORDER["Q"])
        if strong and v.max_raise:
            return "raise", min(max(v.min_raise * 3, v.min_raise), v.max_raise)
        return ("check", 0) if v.to_call == 0 else ("fold", 0)


# --------------------------------------------------------------------------
# One hand
# --------------------------------------------------------------------------

def play_hand(seed: int, agents, blinds=(50, 100), stack=10000):
    """Deal from `seed` and play it out. Returns each seat's chip delta.

    The seed fixes the deck, so the same seed with the agents swapped deals
    the same cards to the same seats - which is what makes the pairing in
    `duplicate_match` cancel the luck instead of merely averaging it.
    """
    random.seed(seed)
    st = NoLimitTexasHoldem.create_state(
        AUTOMATIONS, True, 0, blinds, blinds[1], (stack, stack), 2)

    aggression = [0, 0]  # voluntary bets/raises this hand, by seat
    guard = 0
    while st.status:
        i = st.actor_index
        if i is None:
            break
        guard += 1
        if guard > 400:  # a stuck state must not hang the run
            break

        view = View(
            hole=[repr(c) for c in st.hole_cards[i]],
            board=[repr(c) for row in st.board_cards for c in (row if isinstance(row, list) else [row])],
            pot=st.total_pot_amount,
            to_call=st.checking_or_calling_amount or 0,
            min_raise=st.min_completion_betting_or_raising_to_amount or 0,
            max_raise=st.max_completion_betting_or_raising_to_amount or 0,
            stack=st.stacks[i],
            bb=blinds[1],
            villain_raises=aggression[1 - i],
        )

        action, amount = agents[i].act(view)

        # The agents answer about equity; legality is enforced here, exactly
        # as bot.py enforces it against valid_actions on the real wire.
        if action == "raise" and st.can_complete_bet_or_raise_to():
            lo = st.min_completion_betting_or_raising_to_amount
            hi = st.max_completion_betting_or_raising_to_amount
            st.complete_bet_or_raise_to(min(max(amount, lo), hi))
            aggression[i] += 1
        elif action in ("call", "check") and st.can_check_or_call():
            st.check_or_call()
        elif st.can_fold() and view.to_call > 0:
            st.fold()
        elif st.can_check_or_call():
            st.check_or_call()
        else:
            break

    return [st.stacks[k] - stack for k in range(2)]


def duplicate_match(hands: int, hero, villain, blinds=(50, 100), stack=10000, seed0=1):
    """Play `hands` deals, each twice with the seats swapped.

    Returns hero's per-pair chip results. Each entry already has the card
    luck differenced out, so their mean is a far tighter estimate of the edge
    than the same number of independent hands would give.
    """
    results = []
    for k in range(hands // 2):
        s = seed0 + k
        a = play_hand(s, [hero, villain], blinds, stack)[0]
        b = play_hand(s, [villain, hero], blinds, stack)[1]
        results.append(a + b)
    return results


def report(label, results, bb, hands_per_pair=2):
    n = len(results)
    if n == 0:
        print(f"{label}: no hands")
        return
    total = sum(results)
    hands = n * hands_per_pair
    bb100 = (total / bb) / (hands / 100)
    if n > 1:
        se_pair = statistics.stdev(results) / math.sqrt(n)
        se_bb100 = (se_pair * n / bb) / (hands / 100)
    else:
        se_bb100 = float("nan")
    lo, hi = bb100 - 1.96 * se_bb100, bb100 + 1.96 * se_bb100
    verdict = "wins" if lo > 0 else ("loses" if hi < 0 else "inconclusive")
    print(f"{label:28s} {bb100:+8.1f} bb/100   95% CI [{lo:+.1f}, {hi:+.1f}]   "
          f"{hands:6d} hands   {verdict}")


OPPONENTS = {"reference": Reference, "station": CallingStation, "nit": Nit}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hands", type=int, default=1000)
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--vs", default="all", choices=[*OPPONENTS, "all"])
    ap.add_argument("--ab", action="store_true",
                    help="sweep the knobs instead of playing the fixed bot")
    ap.add_argument("--bb", type=int, default=100)
    args = ap.parse_args()

    if args.ab:
        # Every variant faces the same decks, so the comparison between rows
        # is itself duplicate-dealt and not just each row against its opponent.
        variants = [
            ("shipping", dict()),
            ("no bluffing", dict(bluff_enabled=False)),
            ("realization x0.85 (tighter)", dict(realization_scale=0.85)),
            ("realization x1.15 (looser)", dict(realization_scale=1.15)),
            ("realization off (x1.33)", dict(realization_scale=1.33)),
        ]
        opp = OPPONENTS["reference" if args.vs == "all" else args.vs]()
        print(f"Knob sweep vs {opp.name}, {args.sims} sims/decision, duplicate-dealt\n")
        for label, kw in variants:
            res = duplicate_match(args.hands, PokerCpp(sims=args.sims, **kw), opp,
                                  blinds=(args.bb // 2, args.bb))
            report(label, res, args.bb)
        sys.exit(0)

    hero = PokerCpp(sims=args.sims)
    names = list(OPPONENTS) if args.vs == "all" else [args.vs]
    print(f"pokercpp ({args.sims} sims/decision) vs opponents, duplicate-dealt\n")
    for nm in names:
        res = duplicate_match(args.hands, hero, OPPONENTS[nm](), blinds=(args.bb // 2, args.bb))
        report(f"vs {nm}", res, args.bb)
