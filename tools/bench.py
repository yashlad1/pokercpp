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
        model/advanced_hand_evaluator.cpp model/card.cpp \
        -o chipzen/pokercpp_engine$(python3-config --extension-suffix)
    PYTHONPATH=chipzen python tools/bench.py --hands 2000 --vs reference
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import zlib
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chipzen"))

import pokercpp_engine
from opponent import Opponent
from pokerkit import Automation as A
from pokerkit import NoLimitTexasHoldem, StandardHighHand
from pokerkit.state import ChipsPulling, ChipsPushing

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
                 "stack", "bb", "villain_raises", "hand",
                 "history", "seat", "dealer_seat", "opp_stack", "live_history")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k) if k == "live_history" else kw[k])


class Seeder:
    """A stable nonzero seed per decision, from the hand id (deal seed and the
    agent's own seat, see play_hand), the agent's own decision count within
    that hand and a per-agent salt. Seeded this way, an
    identical spot in two builds draws identical Monte Carlo samples, so the
    paired difference isolates the change instead of sampling noise."""

    def __init__(self, name):
        self.salt = zlib.crc32(name.encode())
        self.count = Counter()
        self.role = 0

    def next(self, hand):
        k = self.count[hand]
        self.count[hand] += 1
        x = (hand * 0x9E3779B97F4A7C15 + k * 0xC2B2AE3D27D4EB4F + self.salt + self.role) & (2**64 - 1)
        x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & (2**64 - 1)
        x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & (2**64 - 1)
        return (x ^ (x >> 31)) or 1


def split_roles(hero, villain):
    """Two agents with the same salt (an A/A run) must not draw the same seeds
    when the swap puts each in the other's seat. Set, never toggled."""
    h, v = getattr(hero, "seeder", None), getattr(villain, "seeder", None)
    if h and v:
        h.role, v.role = 0, int(h.salt == v.salt)


def engine_impl():
    """"metal" when the loaded engine was built with Metal and POKER_NO_METAL is not 1
    (the switch tools/metal_parity.py uses); a USE_METAL build links Metal.framework."""
    if os.environ.get("POKER_NO_METAL") == "1":
        return "cpu"
    with open(pokercpp_engine.__file__, "rb") as f:
        return "metal" if b"Metal.framework" in f.read() else "cpu"


def git_commit():
    try:
        cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                      cwd=cwd, stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                        text=True, cwd=cwd, stderr=subprocess.DEVNULL).strip()
        return sha + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


class PokerCpp:
    """The real engine, with its knobs exposed so variants can be compared."""

    def __init__(self, sims=2000, name="pokercpp", realization_scale=1.0,
                 bluff_enabled=True, memory=True, preflop_realization=None):
        self.preflop_realization = preflop_realization
        self.memory = Opponent() if memory else None
        self.sims = sims
        self.name = name
        self.realization_scale = realization_scale
        self.bluff_enabled = bluff_enabled
        self.seeder = Seeder(name)

    def act(self, v: View):
        floor = 0.0
        if self.memory:
            self.memory.saw(v.hand, v.villain_raises)
            floor = self.memory.range_floor(v.villain_raises)
        d = pokercpp_engine.decide(
            hole=v.hole, board=v.board, pot=v.pot, to_call=v.to_call,
            min_raise=v.min_raise, max_raise=v.max_raise, stack=v.stack,
            bb=v.bb, sims=self.sims, villain_raises=v.villain_raises,
            realization_scale=self.realization_scale,
            bluff_enabled=self.bluff_enabled, range_floor=floor,
            seed=self.seeder.next(v.hand),
            **({} if self.preflop_realization is None
               else {"preflop_realization": self.preflop_realization}),
        )
        return d["action"], d["amount"]


REAL_DECIDE = pokercpp_engine.decide


class Bot:
    """The shipped wire adapter (chipzen/bot.py) as hero: the View is rebuilt
    into a chipzen GameState the way the platform sends it, bot.decide() runs
    unchanged, and its Action is mapped back to bench terms. Exercises blind
    reading, raise counting, legality mapping and opponent memory keyed by
    hand number. The engine seed comes from a wrapper on pokercpp_engine.decide
    (bot.py gets no bench code), keyed like PokerCpp's, so parity is exact."""

    name = "bot"

    def __init__(self, sb, bb, stack, sims=2000, history="full", hand_number="full", wire="bench"):
        import bot as bot_mod
        from chipzen import GameState
        from chipzen.models import Card
        self.GameState, self.Card = GameState, Card
        self.history, self.sims, self.zero = history, sims, hand_number == "zero"
        self.seen_hand = None
        self.live = wire == "live"
        self.seeder, self.cur = Seeder("pokercpp"), 0
        real = REAL_DECIDE

        def seeded(**kw):
            kw["sims"] = self.sims
            kw["seed"] = self.seeder.next(self.cur)
            self.last_kw = kw
            return real(**kw)

        pokercpp_engine.decide = seeded
        self.bot = bot_mod.PokerCppBot()
        self.bot.on_match_start({"game_config": {
            "small_blind": sb, "big_blind": bb, "ante": 0, "starting_stack": stack}})

    def act(self, v: View):
        self.cur = v.hand
        if v.hand != self.seen_hand:
            self.seen_hand = v.hand
            self.bot.on_round_start({})
        to_call, stack, n = v.to_call, v.stack, len(v.board)
        can_raise = v.max_raise > 0
        valid = ["fold"] if to_call > 0 else []
        if to_call == 0:
            valid.append("check")
        elif to_call < stack:
            valid.append("call")
        if can_raise:
            valid.append("raise")
        if self.live:
            if 0 < stack <= to_call:
                valid = ["fold", "call"]  # live offers an all-in call as a plain call
        elif can_raise or (0 < stack <= to_call):
            valid.append("all_in")
        hist = [e for e in ([{**e, "is_timeout": False} for e in v.live_history] if self.live else v.history)
                if self.history == "full" or not e["action"].startswith("post_")]
        st = self.GameState(
            hand_number=0 if self.zero else v.hand + 1,
            phase={0: "preflop", 3: "flop", 4: "turn", 5: "river"}[n],
            hole_cards=[self.Card.from_str(c) for c in v.hole],
            board=[self.Card.from_str(c) for c in v.board],
            pot=v.pot, your_stack=stack, opponent_stacks=[v.opp_stack],
            your_seat=v.seat, dealer_seat=v.dealer_seat, to_call=to_call,
            min_raise=v.min_raise, max_raise=v.max_raise,
            valid_actions=valid, action_history=hist)
        a = self.bot.decide(st)
        if a.action == "raise":
            return "raise", a.amount
        if a.action == "all_in":
            return ("call", 0) if to_call >= stack else ("raise", v.max_raise)
        return a.action, 0

    def hand_over(self, res, seat):
        """The end-of-hand message as the live server sends it. Seats swap under
        duplicate dealing and the hero may not have acted this hand (the big blind
        after a fold), so the seat is set here."""
        self.bot.my_seat = seat
        res = dict(res, hand_number=0 if self.zero else res["hand_number"])
        self.bot.on_round_result({"type": "round_result", "result": res})


class September:
    """The bot as shipped in September (c057f40), built as pokercpp_engine_base.
    No opponent memory: the point is to measure what the memory work added."""

    name = "september"

    def __init__(self, sims=2000):
        self.sims = sims
        self.seeder = Seeder(self.name)
        try:
            pokercpp_engine_base.decide(hole=["As", "Kd"], board=[], pot=150, to_call=50,
                                        min_raise=200, max_raise=1000, stack=1000,
                                        bb=100, sims=10, seed=1)
            self.seeded = True
        except TypeError:
            self.seeded = False

    def act(self, v: View):
        extra = {"seed": self.seeder.next(v.hand)} if self.seeded else {}
        d = pokercpp_engine_base.decide(
            hole=v.hole, board=v.board, pot=v.pot, to_call=v.to_call,
            min_raise=v.min_raise, max_raise=v.max_raise, stack=v.stack,
            bb=v.bb, sims=self.sims, villain_raises=v.villain_raises, **extra,
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


class ThreeBet(Reference):
    """Reference, except it re-raises our first preflop raise to 3x with any pair, ace, two cards
    9 or higher or suited connector 54s+, and against our re-raise calls with TT+ or AK, else folds."""

    name = "threebet"

    def _preflop(self, v: View):
        r = sorted((RANK_ORDER[c[0]] for c in v.hole), reverse=True)
        suited = v.hole[0][1] == v.hole[1][1]
        if v.villain_raises >= 2:
            if (r[0] == r[1] and r[0] >= RANK_ORDER["T"]) or r[:2] == [RANK_ORDER["A"], RANK_ORDER["K"]]:
                return ("call", 0) if v.to_call else ("check", 0)
            return ("fold", 0) if v.to_call else ("check", 0)
        if v.villain_raises == 1 and v.to_call > 0 and v.max_raise > 0:
            if (r[0] == r[1] or r[0] == RANK_ORDER["A"] or r[1] >= RANK_ORDER["9"]
                    or (suited and r[0] - r[1] == 1 and r[1] >= RANK_ORDER["4"])):
                raise_to = (v.pot + v.to_call) // 2  # to_call plus our own posted blind, heads-up
                return "raise", min(max(3 * raise_to, v.min_raise), v.max_raise)
        return super()._preflop(v)


class Sizer(Reference):
    """Reference, except when checked to postflop it bets 1/3 pot with two pair or better,
    1.5x pot with no pair, and checks one pair."""

    name = "sizer"

    def _postflop(self, v: View):
        if v.to_call == 0 and v.max_raise > 0:
            counts = sorted(Counter(c[0] for c in v.hole + v.board).values(), reverse=True)
            klass = 3 if counts[0] >= 3 else (2 if counts[:2] == [2, 2] else (1 if counts[0] == 2 else 0))
            if klass != 1:
                size = v.pot // 3 if klass >= 2 else v.pot * 3 // 2
                return "raise", min(max(size, v.min_raise), v.max_raise)
            return "check", 0
        return super()._postflop(v)


class Bluffer(Reference):
    """Reference, except a fixed share p of its no-pair postflop hands (chosen per deal) bet
    0.66 pot on every street and fold to any raise. A bot that cannot beat this folds too
    much to bluffs that are only some of the time."""

    def __init__(self, p, name):
        self.p, self.name = p, name

    def _postflop(self, v: View):
        counts = sorted(Counter(c[0] for c in v.hole + v.board).values(), reverse=True)
        if counts[0] == 1 and zlib.crc32(f"{v.hole}{v.board[:3]}".encode()) / 2**32 < self.p:
            if v.to_call == 0 and v.max_raise > 0:
                return "raise", min(max(int(v.pot * 0.66), v.min_raise), v.max_raise)
            return ("check", 0) if v.to_call == 0 else ("fold", 0)
        return super()._postflop(v)


def _preflop_pct():
    """Fraction of the 1326 combos ranked ahead of each hand class (midpoint of the
    class), from montecarlo/preflop_ranks.h: equity against a random hand, measured
    by this repo's simulator. Key (high rank, low rank, suited)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "montecarlo", "preflop_ranks.h")
    out, cum = {}, 0
    for hi, lo, suited, combos in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(true|false)\s*,\s*(\d+)\},", open(path).read()):
        out[(int(hi), int(lo), suited == "true")] = (cum + int(combos) / 2) / 1326
        cum += int(combos)
    return out


PREFLOP_PCT = _preflop_pct()


def _pushfold_table():
    """{stack in bb: 169 push percentages}, columns in PREFLOP_PCT key order, from tools/pushfold_table.h."""
    txt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pushfold_table.h")).read()
    return {float(s): [int(x) for x in row.split(",")] for row, s in re.findall(r"\{([\d,]+)\},\s*//\s*([\d.]+) bb", txt)}


PUSHFOLD = _pushfold_table()
PUSHFOLD_COL = {k: i for i, k in enumerate(PREFLOP_PCT)}


class PushFold(Reference):
    """Reference, except as the small blind facing only the big blind at 20 bb or less effective it plays
    the solved heads-up push/fold table: all-in with the table's frequency for its hand class, else fold."""

    name = "pushfold"

    def _preflop(self, v: View):
        eff = min(v.stack + v.bb - v.to_call, v.opp_stack + v.bb)  # chips at hand start
        if v.villain_raises == 0 and v.to_call > 0 and eff <= 20 * v.bb:
            r = sorted((RANK_ORDER[c[0]] + 2 for c in v.hole), reverse=True)
            col = PUSHFOLD_COL[(r[0], r[1], v.hole[0][1] == v.hole[1][1] and r[0] != r[1])]
            f = PUSHFOLD[max([s for s in PUSHFOLD if s * v.bb <= eff] or [1.0])][col]
            if zlib.crc32(f"{v.hole}{v.hand}".encode()) / 2**32 < f / 100:
                return "raise", v.max_raise
            return "fold", 0
        return super()._preflop(v)


class LooseBluffer(Bluffer):
    """Bluffer postflop. Preflop modelled on a live opponent: first in as the small blind
    it raises to 3 bb with the top 58% of hands, limps the next 27% and folds the rest;
    facing a raise it re-raises to 3x with the top 4%, calls to the top 75% and folds the
    rest. The big blind checks its option after a limp."""

    def _preflop(self, v: View):
        r = sorted((RANK_ORDER[c[0]] + 2 for c in v.hole), reverse=True)
        q = PREFLOP_PCT[(r[0], r[1], v.hole[0][1] == v.hole[1][1] and r[0] != r[1])]
        if v.villain_raises == 0:
            if v.to_call == 0:
                return "check", 0
            raise_to, raise_cut, call_cut = 3 * v.bb, 0.58, 0.85
        else:
            raise_to, raise_cut, call_cut = 3 * (v.pot + v.to_call) // 2, 0.04, 0.75
        if q < raise_cut and v.max_raise:
            return "raise", min(max(raise_to, v.min_raise), v.max_raise)
        return ("call", 0) if q < call_cut else ("fold", 0)


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


class Maniac:
    """Shoves every hand. A bot that cannot beat this folds too much to all-ins."""
    name = "maniac"

    def act(self, v: View):
        if v.max_raise:
            return "raise", v.max_raise
        return ("check", 0) if v.to_call == 0 else ("call", 0)


class Aggro:
    """Raises big at every chance. A bot that cannot beat this is pushed off too many pots."""
    name = "aggro"

    def act(self, v: View):
        if v.max_raise:
            return "raise", min(max(3 * v.min_raise, v.pot), v.max_raise)
        return ("check", 0) if v.to_call == 0 else ("call", 0)


class LoosePassive:
    """Never raises, calls any bet up to pot size and folds to bigger ones. A bot that
    cannot beat this is not extracting value from weak, passive ranges."""
    name = "loosepassive"

    def act(self, v: View):
        if v.to_call == 0:
            return "check", 0
        return ("call", 0) if v.to_call <= v.pot - v.to_call else ("fold", 0)


def knobs_settings(deal_seed):
    """The engine knobs for one deal seed (a pair of duplicate hands). Pure in the seed."""
    r = random.Random(deal_seed)
    return dict(realization_scale=r.choice([0.8, 0.9, 1.0, 1.1, 1.2]), bluff_enabled=r.choice([True, False]),
                memory=r.choice([True, False]), preflop_realization=r.choice([0.65, 0.75, 0.85]))


class Knobs:
    """The engine at 500 sims with its settings drawn per hand pair, so the hero meets many variants.
    A fresh engine per hand: its memory and seeds are those of an engine that saw only this hand."""

    name = "knobs"

    def __init__(self):
        self.hand = None

    def act(self, v: View):
        if v.hand != self.hand:
            self.hand = v.hand
            self.engine = PokerCpp(sims=500, name="knobs", **knobs_settings(v.hand // 2))
        return self.engine.act(v)


class Switcher:
    """Plays like Nit for 30 hands, then like Maniac for 30, and repeats. A bot that
    cannot follow this is slow to notice a change of style."""
    name = "switcher"

    def __init__(self):
        self.seen, self.nit, self.maniac = set(), Nit(), Maniac()

    def act(self, v: View):
        self.seen.add(v.hand)
        return (self.maniac if (len(self.seen) - 1) // 30 % 2 else self.nit).act(v)


class RandomLegal:
    """Picks any legal action at random. A bot that cannot beat this has a leak
    somewhere basic. Uses its own RNG, reseeded each decision from its own hole
    cards and the view, so it never touches the deck's RNG stream. (The two
    seat-swapped plays do not see the same draws: it holds different cards.)"""
    name = "random"

    def __init__(self):
        self.rng = random.Random(0)

    def act(self, v: View):
        self.rng.seed(f"{v.hole}{v.board}{v.pot}{v.to_call}")
        options = ["call"] + (["fold"] if v.to_call > 0 else []) + (["raise"] if v.max_raise > 0 else [])
        pick = self.rng.choice(options)
        if pick == "raise":
            return "raise", self.rng.randint(v.min_raise, v.max_raise)
        return (pick, 0)


HAND_RANK = {"HIGH_CARD": "High Card", "ONE_PAIR": "Pair", "TWO_PAIR": "Two Pair",
             "THREE_OF_A_KIND": "Three of a Kind", "STRAIGHT": "Straight", "FLUSH": "Flush",
             "FULL_HOUSE": "Full House", "FOUR_OF_A_KIND": "Four of a Kind",
             "STRAIGHT_FLUSH": "Straight Flush"}


def round_result(st, hand, live, holes):
    """The `result` of the live server's round_result message for a finished hand.
    `holes` are the dealt cards: pokerkit mucks the loser's at showdown. As live,
    payouts are what each winner pulls (their own uncalled bet included) and pot is
    the matched pot."""
    pushed, pulled = 0, [0, 0]
    for op in st.operations:
        if isinstance(op, ChipsPushing):
            pushed += sum(op.amounts)
        elif isinstance(op, ChipsPulling):
            pulled[op.player_index] += op.amount
    folded = live[-1]["action"] == "fold"
    showdown = []
    if not folded:
        board = "".join(repr(c) for row in st.board_cards for c in (row if isinstance(row, list) else [row]))
        for k in (0, 1):
            h = StandardHighHand.from_game("".join(holes[k]), board)
            showdown.append({"seat": k, "hole_cards": holes[k],
                             "hand_rank": HAND_RANK[h.entry.label.name],
                             "best_hand": [repr(c) for c in h.cards]})
    return {"hand_number": hand + 1, "winner_seats": [k for k in (0, 1) if pulled[k] > 0],
            "pot": pushed * (2 if folded else 1),
            "payouts": [{"seat": k, "amount": pulled[k]} for k in (0, 1) if pulled[k] > 0],
            "showdown": showdown, "action_history": live, "stacks": list(st.stacks)}


def raise_amount_legal(amount, min_raise, max_raise):
    """The live server's band rule: a short stack (min_raise > max_raise) may only raise to max_raise."""
    return amount == max_raise if min_raise > max_raise else min_raise <= amount <= max_raise


def play_hand(seed: int, agents, blinds=(50, 100), stack=10000, stacks=None):
    """Deal from `seed` and play it out. Returns each seat's chip delta.

    The seed fixes the deck, so the same seed with the agents swapped deals
    the same cards to the same seats - which is what makes the pairing in
    `duplicate_match` cancel the luck instead of merely averaging it.
    """
    start = (stack, stack) if stacks is None else tuple(stacks)
    random.seed(seed)
    st = NoLimitTexasHoldem.create_state(
        AUTOMATIONS, True, 0, blinds, blinds[1], start, 2)

    holes = [[repr(c) for c in st.hole_cards[k]] for k in (0, 1)]
    aggression = [0, 0]  # voluntary bets/raises this hand, by seat
    # SDK-shaped log of the hand so far, for the Bot agent. pokerkit heads-up: the small blind is the dealer
    # and acts first preflop.
    sb = 0 if st.bets[0] < st.bets[1] else 1
    history = [
        {"seat": sb, "action": "post_small_blind", "amount": st.bets[sb], "phase": "preflop", "is_timeout": False},
        {"seat": 1 - sb, "action": "post_big_blind", "amount": st.bets[1 - sb], "phase": "preflop", "is_timeout": False},
    ]
    live = [dict(e) for e in history]
    for e in live:
        del e["is_timeout"]
    phases = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
    guard = 0
    while st.status:
        i = st.actor_index
        if i is None:
            break
        guard += 1
        if guard > 400:
            break

        view = View(
            hole=[repr(c) for c in st.hole_cards[i]],
            board=[repr(c) for row in st.board_cards for c in (row if isinstance(row, list) else [row])],
            pot=st.total_pot_amount,
            # Uncapped, as the platform sends it: pokerkit's own amount is capped at our stack, which would hide the
            # engine's cap.
            to_call=max(max(st.bets) - st.bets[i], 0),
            min_raise=st.min_completion_betting_or_raising_to_amount or 0,
            max_raise=st.max_completion_betting_or_raising_to_amount or 0,
            stack=st.stacks[i],
            bb=blinds[1],
            villain_raises=aggression[1 - i],
            hand=seed * 2 + i,
            history=list(history), seat=i, dealer_seat=sb, opp_stack=st.stacks[1 - i],
            live_history=list(live),
        )
        phase = phases.get(len(view.board), "river")

        # The agents answer about equity; legality is enforced here, as bot.py enforces it against valid_actions on the wire.
        action, amount = agents[i].act(view)
        if hasattr(agents[i], "coerced"):  # the hero only: count what the live server would reject
            offered = {"check"} if view.to_call == 0 else {"fold", "call"}
            if view.max_raise > 0 and not 0 < view.stack <= view.to_call:
                offered.add("raise")
            agents[i].coerced += action not in offered or (
                action == "raise" and not raise_amount_legal(amount, view.min_raise, view.max_raise))

        if action == "raise" and st.can_complete_bet_or_raise_to():
            lo = st.min_completion_betting_or_raising_to_amount
            hi = st.max_completion_betting_or_raising_to_amount
            to = min(max(amount, lo), hi)
            st.complete_bet_or_raise_to(to)
            aggression[i] += 1
            entry = ("all_in" if to >= hi else "raise", to)
            live_label = "raise"  # live labels every bet and all-in "raise"
        elif action in ("call", "check") and st.can_check_or_call():
            st.check_or_call()
            entry = (("check", 0) if view.to_call == 0 else
                     ("all_in" if view.to_call >= view.stack else "call", min(view.to_call, view.stack)))
            live_label = "check" if view.to_call == 0 else "call"
        elif st.can_fold() and view.to_call > 0:
            st.fold()
            entry = ("fold", 0)
            live_label = "fold"
        elif st.can_check_or_call():
            st.check_or_call()
            entry = (("check", 0) if view.to_call == 0 else
                     ("all_in" if view.to_call >= view.stack else "call", min(view.to_call, view.stack)))
            live_label = "check" if view.to_call == 0 else "call"
        else:
            break
        history.append({"seat": i, "action": entry[0], "amount": entry[1],
                        "phase": phase, "is_timeout": False})
        live.append({"seat": i, "action": live_label, "amount": entry[1], "phase": phase})

    if any(hasattr(a, "hand_over") for a in agents):
        res = round_result(st, seed, live, holes)
        for k, a in enumerate(agents):
            if hasattr(a, "hand_over"):
                a.hand_over(dict(res, hand_number=seed * 2 + k + 1), k)

    return [st.stacks[k] - start[k] for k in range(2)]


def duplicate_match(hands: int, hero, villain, blinds=(50, 100), stack=10000, seed0=1):
    """Play `hands` deals, each twice with the seats swapped.

    Returns hero's per-pair chip results. Each entry already has the card
    luck differenced out, so their mean is a far tighter estimate of the edge
    than the same number of independent hands would give.
    """
    split_roles(hero, villain)
    hero.coerced = 0
    results = []
    for k in range(hands // 2):
        s = seed0 + k
        a = play_hand(s, [hero, villain], blinds, stack)[0]
        b = play_hand(s, [villain, hero], blinds, stack)[1]
        results.append(a + b)
    return results


def bb100_ci(results, bb, hands_per_pair=2):
    """Mean in bb/100 and its 95% interval, from per-pair chip results."""
    n = len(results)
    hands = n * hands_per_pair
    bb100 = (sum(results) / bb) / (hands / 100)
    if n > 1:
        se_pair = statistics.stdev(results) / math.sqrt(n)
        se_bb100 = (se_pair * n / bb) / (hands / 100)
    else:
        se_bb100 = float("nan")
    return bb100, bb100 - 1.96 * se_bb100, bb100 + 1.96 * se_bb100


def report(label, results, bb, hands_per_pair=2):
    n = len(results)
    if n == 0:
        print(f"{label}: no hands")
        return
    hands = n * hands_per_pair
    bb100, lo, hi = bb100_ci(results, bb, hands_per_pair)
    verdict = "wins" if lo > 0 else ("loses" if hi < 0 else "inconclusive")
    print(f"{label:28s} {bb100:+8.1f} bb/100   95% CI [{lo:+.1f}, {hi:+.1f}]   "
          f"{hands:6d} hands   {verdict}")


OPPONENTS = {"reference": Reference, "station": CallingStation, "nit": Nit,
             "maniac": Maniac, "aggro": Aggro, "switcher": Switcher,
             "loosepassive": LoosePassive, "random": RandomLegal,
             "bluff0": lambda: Bluffer(0.0, "bluff0"), "bluff25": lambda: Bluffer(0.25, "bluff25"),
             "bluff50": lambda: Bluffer(0.5, "bluff50"),
             "loosebluff0": lambda: LooseBluffer(0.0, "loosebluff0"),
             "loosebluff25": lambda: LooseBluffer(0.25, "loosebluff25"),
             "loosebluff50": lambda: LooseBluffer(0.5, "loosebluff50"),
             "threebet": ThreeBet, "sizer": Sizer, "pushfold": PushFold, "knobs": Knobs}

try:
    import pokercpp_engine_base
    OPPONENTS["september"] = September
except ImportError:
    pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hands", type=int, default=1000)
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--vs", default="all", choices=[*OPPONENTS, "all"])
    ap.add_argument("--ab", action="store_true",
                    help="sweep the knobs instead of playing the fixed bot")
    ap.add_argument("--bb", type=int, default=100)
    ap.add_argument("--stack", type=int, default=100,
                    help="starting stack in big blinds")
    ap.add_argument("--seed0", type=int, default=1,
                    help="first deal seed; pair k uses seed0 + k")
    ap.add_argument("--hero", default="engine", choices=["engine", "bot"],
                    help="engine: call the C++ engine directly; bot: run chipzen/bot.py")
    ap.add_argument("--wire", choices=["bench", "live"],
                    help="with --hero bot: the live server's view (no all_in, live labels; default) or the bench view; "
                         "the engine hero ignores it and records bench (default)")
    ap.add_argument("--history", default="full", choices=["full", "noblinds"],
                    help="with --hero bot: include the blind posts in action_history or omit them")
    ap.add_argument("--hand-number", default="full", choices=["full", "zero"],
                    help="with --hero bot: send real hand numbers or hand_number=0")
    ap.add_argument("--realization-scale", type=float, default=1.0,
                    help="engine hero: realization scale (1.0 = shipping)")
    ap.add_argument("--preflop-realization", type=float, default=None,
                    help="engine hero: preflop realization (unset = shipping 0.75)")
    ap.add_argument("--no-bluff", action="store_true", help="engine hero: bluff_enabled=False")
    ap.add_argument("--no-memory", action="store_true", help="engine hero: no opponent memory")
    ap.add_argument("--dump", metavar="PATH",
                    help="write per-pair results as JSON, for tools/paired.py")
    args = ap.parse_args()
    if args.wire and args.hero == "engine":
        print("note: --wire is ignored for --hero engine (recorded as bench)", file=sys.stderr)
    args.wire = (args.wire or "live") if args.hero == "bot" else "bench"
    if args.dump and (args.ab or args.vs == "all"):
        ap.error("--dump needs a single opponent: use --vs NAME without --ab")
    knobs = dict(realization_scale=args.realization_scale,
                 bluff_enabled=not args.no_bluff, memory=not args.no_memory,
                 preflop_realization=args.preflop_realization)
    defaults = dict(realization_scale=1.0, bluff_enabled=True, memory=True, preflop_realization=None)
    if args.hero == "bot" and knobs != defaults:
        ap.error("--realization-scale/--preflop-realization/--no-bluff/--no-memory need --hero engine: chipzen/bot.py has no such knobs")
    if args.ab and knobs != defaults:
        ap.error("the knob flags do not apply to --ab, which sweeps them itself")

    if args.ab:
        variants = [
            ("shipping", dict()),
            ("no memory", dict(memory=False)),
            ("no bluffing", dict(bluff_enabled=False)),
            ("realization x0.85 (tighter)", dict(realization_scale=0.85)),
            ("realization x1.15 (looser)", dict(realization_scale=1.15)),
            ("realization off (x1.33)", dict(realization_scale=1.33)),
        ]
        opp = OPPONENTS["reference" if args.vs == "all" else args.vs]()
        print(f"Knob sweep vs {opp.name}, {args.sims} sims/decision, duplicate-dealt, {args.stack} bb deep\n")
        runs = []
        for label, kw in variants:
            # Every variant faces the same decks, so rows are duplicate-dealt against each other, not just against the opponent.
            res = duplicate_match(args.hands, PokerCpp(sims=args.sims, **kw), opp,
                                  blinds=(args.bb // 2, args.bb),
                                  stack=args.stack * args.bb, seed0=args.seed0)
            report(label, res, args.bb)
            runs.append((label, res))
        print("\nPaired vs shipping (per-pair difference, same deals):")
        base = runs[0][1]
        for label, res in runs[1:]:
            d = [x - y for x, y in zip(res, base)]
            bb100, lo, hi = bb100_ci(d, args.bb)
            verdict = "better" if lo > 0 else ("worse" if hi < 0 else "inconclusive")
            print(f"{label:28s} {bb100:+8.1f} bb/100   95% CI [{lo:+.1f}, {hi:+.1f}]   {verdict}")
        sys.exit(0)

    names = list(OPPONENTS) if args.vs == "all" else [args.vs]
    print(f"pokercpp ({args.sims} sims/decision) vs opponents, duplicate-dealt, {args.stack} bb deep\n")
    for nm in names:
        hero = (Bot(args.bb // 2, args.bb, args.stack * args.bb, args.sims, args.history, args.hand_number, wire=args.wire)
                if args.hero == "bot" else PokerCpp(sims=args.sims, **knobs))
        res = duplicate_match(args.hands, hero, OPPONENTS[nm](), blinds=(args.bb // 2, args.bb),
                             stack=args.stack * args.bb, seed0=args.seed0)
        report(f"vs {nm}", res, args.bb)
        print(f"coerced {hero.coerced}")
        if args.dump:
            with open(args.dump, "w") as f:
                json.dump({"seed0": args.seed0, "bb": args.bb, "stack_bb": args.stack,
                           "opponent": nm, "results": res, **knobs,
                           "meta": dict(sims=args.sims, hero=args.hero, history=args.history,
                                        hand_number=args.hand_number, wire=args.wire, impl=engine_impl(),
                                        commit=git_commit(), knobs=knobs, coerced=hero.coerced)}, f)
