#!/usr/bin/env python3
"""Offline lab for #37: how often does today's hard top-X% range hold the hand Slumbot showed,
against a board-aware weighted range (a Bayesian update of each combo's weight by his actions)?

  range_lab.py LOG [LOG ...] [--out FILE.json]

Measurement only; nothing here ships in the bot. The preflop ranking is parsed from
montecarlo/preflop_ranks.h, the same table the engine reads.
"""
import argparse
import collections
import itertools
import json
import math
import pathlib
import re
import sys

from pokerkit import StandardHighHand

HERE = pathlib.Path(__file__).resolve().parent
RANKS = "23456789TJQKA"
DECK = [r + s for r in RANKS for s in "cdhs"]
STREETS = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
NBOARD = {0: 0, 3: 3, 4: 4, 5: 5}

_TXT = (HERE.parent / "montecarlo" / "preflop_ranks.h").read_text()
RANKED = [(int(h), int(lo), s == "true", int(n)) for h, lo, s, n in
          re.findall(r"\{\s*(\d+),\s*(\d+),\s*(true|false)\s*,\s*(\d+)\}", _TXT)]
assert len(RANKED) == 169 and sum(c[3] for c in RANKED) == 1326
CLASS_IDX = {(h, lo, s): i for i, (h, lo, s, _) in enumerate(RANKED)}


def _key(a, b):
    a, b = sorted((a, b), key=DECK.index)
    return a + b


def _cls(combo):
    a, b = combo[:2], combo[2:]
    r1, r2 = RANKS.index(a[0]) + 2, RANKS.index(b[0]) + 2
    return CLASS_IDX[(max(r1, r2), min(r1, r2), a[1] == b[1] and r1 != r2)]


def live_combos(dead):
    live = [c for c in DECK if c not in set(dead)]
    return [a + b for a, b in itertools.combinations(live, 2)]


def hard_range(frac, dead=()):
    wanted = int(frac * 1326 + 0.5)
    allowed, cum = set(), 0
    for i, c in enumerate(RANKED):
        if cum >= wanted:
            break
        allowed.add(i)
        cum += c[3]
    return {c for c in live_combos(dead) if _cls(c) in allowed}


def _sig(x):
    return 1 / (1 + math.exp(-x))


def prior_weights(dead=()):
    s = strength_pct([], dead)
    return {c: 0.05 + 0.9 * _sig(12 * (v - 0.5)) for c, v in s.items()}


def strength_pct(board, dead=()):
    """Share of the other live combos this one strictly beats; ties share the lowest rank."""
    cs = live_combos(set(dead) | set(board))
    if not board:
        key = {c: -_cls(c) for c in cs}
    else:
        b = "".join(board)
        key = {c: StandardHighHand.from_game(c, b) for c in cs}
    order = sorted(cs, key=key.get)
    out, first = {}, 0
    for i, c in enumerate(order):
        if i and key[c] != key[order[i - 1]]:
            first = i
        out[c] = first / (len(order) - 1)
    return out


def p_action(action, s, raise_cut, fold_cut, k=12.0, eps=0.05):
    up = _sig(k * (s - raise_cut))
    down = _sig(k * (fold_cut - s))
    fold = down * (1 - up)
    p = {"raise": up, "fold": fold, "call": max(0.0, 1 - up - fold), "bet": up, "check": 1 - up}
    return eps + (1 - 2 * eps) * p[action]


def update(w, action, s, raise_rate, fold_rate, alpha=0.05):
    w2 = {c: v * p_action(action, s[c], 1 - raise_rate, fold_rate) for c, v in w.items()}
    mean = sum(w2.values()) / len(w2)
    return {c: (1 - alpha) * v + alpha * mean for c, v in w2.items()}


def in_top_mass(w, shown, mass):
    total, acc = sum(w.values()), 0.0
    for c in sorted(w, key=w.get, reverse=True):
        acc += w[c]
        if c == shown:
            return True
        if acc >= mass * total:
            return False
    return False


def log_score(w, shown):
    return math.log(w[shown] * len(w) / sum(w.values()))


# ---- the log walk ----------------------------------------------------------------------

def slumbot_actions(h):
    """[(street, action)] for Slumbot, action in raise/bet/call/check/fold."""
    me = 1 - h["client_pos"]
    out = []
    for st, text in zip((0, 3, 4, 5), h["action"].split("/")):
        facing = st == 0
        for i, m in enumerate(re.findall(r"b\d+|[ckf]", text)):
            who = ((1 if st == 0 else 0) + i) % 2
            a = {"k": "check", "c": "call", "f": "fold"}.get(m) or ("raise" if facing else "bet")
            if who == me:
                out.append((st, a))
            facing = m[0] == "b"
    return out


def rates(hands):
    """His pooled rates over the logs: (raise, fold) when facing a bet, bet share when not."""
    n = collections.Counter(a for h in hands for _, a in slumbot_actions(h))
    fc = n["raise"] + n["call"] + n["fold"] or 1
    nf = n["bet"] + n["check"] or 1
    cl = lambda x: min(0.95, max(0.02, x))
    return {"face": (cl(n["raise"] / fc), cl(n["fold"] / fc)), "open": (cl(n["bet"] / nf), 0.0)}


def measure(hands):
    R = rates(hands)
    acc = collections.defaultdict(lambda: [0, 0, 0, 0.0])  # n, hard, weighted, log
    for h in hands:
        by_st = collections.defaultdict(list)
        for d in h["decisions"]:
            by_st[d["street"]].append(d)
        acts = slumbot_actions(h)
        shown = _key(*h["bot_hole"])
        w = None
        for st in (0, 3, 4, 5):
            board = h["board"][:NBOARD[st]]
            if st and len(board) < NBOARD[st]:
                break
            dead = set(h["hole"]) | set(board)
            w = prior_weights(dead) if w is None else {c: v for c, v in w.items() if not set((c[:2], c[2:])) & dead}
            mine = [a for s_, a in acts if s_ == st]
            if mine:
                s = strength_pct(board, dead)
                for a in mine:
                    w = update(w, a, s, *R["open" if a in ("bet", "check") else "face"])
            for d in by_st[st]:
                row = acc[st]
                row[0] += 1
                row[1] += shown in hard_range(d["range"], dead)
                row[2] += in_top_mass(w, shown, d["range"])
                row[3] += log_score(w, shown)
    return {STREETS[st]: {"n": r[0], "covered_hard_pct": 100 * r[1] / r[0],
                          "covered_weighted_pct": 100 * r[2] / r[0], "mean_log_score": r[3] / r[0]}
            for st, r in sorted(acc.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    hands = [json.loads(line) for p in a.logs for line in open(p) if line.strip()]
    streets = measure(hands)
    print(f"{'street':8}{'n':>6}{'hard %':>9}{'weighted %':>12}{'mean log':>10}")
    for name, r in streets.items():
        print(f"{name:8}{r['n']:>6}{r['covered_hard_pct']:>9.1f}{r['covered_weighted_pct']:>12.1f}"
              f"{r['mean_log_score']:>10.3f}")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps({"streets": streets}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
