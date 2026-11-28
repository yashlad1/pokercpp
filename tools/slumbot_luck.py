#!/usr/bin/env python3
"""Luck-adjusted Slumbot scoring (#190 P1). Analysis only.

  tools/slumbot_luck.py LOG [LOG ...] [--out FILE.json]

A hand where both players were all-in, the last all-in bet was called before the river and bot_hole is
known is scored by our equity at that moment: adjusted = eq * pot - our contribution. Every other hand
keeps its winnings. eq is exact over every board completion when at most 2 cards are to come (a tie
counts half); preflop it is a seeded Monte Carlo of 20,000 boards, so output repeats exactly.
bb/100 = chips / hands (blinds 50/100); interval = mean +- 1.96 * sample SD / sqrt(n).
"""
import argparse
import itertools
import json
import math
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pokerkit import StandardHighHand
from slumbot import STACK, replay

DECK = [r + s for r in "23456789TJQKA" for s in "cdhs"]
BOARD_AT = {0: 0, 1: 3, 2: 4}  # board cards visible when the money went in, by street
MC_BOARDS, SEED = 20000, 190
_cache = {}


def equity(hero, villain, board):
    key = (tuple(sorted(hero)), tuple(sorted(villain)), tuple(board))
    if key in _cache:
        return _cache[key]
    rest = [c for c in DECK if c not in set(hero + villain + board)]
    k = 5 - len(board)
    if k <= 2:
        runs = itertools.combinations(rest, k)
    else:  # ponytail: preflop only; 20,000 boards, SE about 0.003
        rng = random.Random(SEED)
        runs = (rng.sample(rest, k) for _ in range(MC_BOARDS))
    score = n = 0
    for run in runs:
        b = "".join(board) + "".join(run)
        a = StandardHighHand.from_game("".join(hero), b)
        v = StandardHighHand.from_game("".join(villain), b)
        score += 1 if a > v else 0.5 if a == v else 0
        n += 1
    _cache[key] = score / n
    return _cache[key]


def all_in_street(h):
    """Street of the called all-in when it came before the river and bot_hole is known, else None."""
    if not h.get("bot_hole"):
        return None
    r = replay(h["action"])
    if r["over"] != "showdown" or r["street"] > 2 or r["total"] != [STACK, STACK]:
        return None
    return r["street"]


def pot_before_deal(action, s):
    """Both players' total contributions after all betting on streets before deal s (1 flop, 2 turn, 3 river)."""
    parts = action.split("/")
    return sum(replay("/".join(parts[:s]))["total"])


def deals(h):
    """Board lengths at each deal that happened, in order: [3], [3, 4] or [3, 4, 5], or none."""
    return [k for k in (3, 4, 5) if len(h["board"]) >= k] if h.get("bot_hole") else []


def boards_needed(h):
    st = all_in_street(h)
    ks = ([BOARD_AT[st]] if st is not None else []) + ([0] + deals(h) if deals(h) else [])
    return [(tuple(sorted(h["hole"])), tuple(sorted(h["bot_hole"])), tuple(h["board"][:k])) for k in ks]


def _fill(key):
    return key, equity(*map(list, key))


def prefetch(hands):
    """Fill the equity cache; many distinct preflop Monte Carlos go across processes."""
    todo = sorted({k for h in hands for k in boards_needed(h)} - set(_cache))
    if len(todo) > 20:  # ponytail: a process pool only when it pays for its start-up
        import multiprocessing
        with multiprocessing.Pool() as pool:
            _cache.update(pool.map(_fill, todo, chunksize=4))


def score(h):
    """(raw, all-in adjusted, was all-in adjusted, street adjusted, was street adjusted) for one hand."""
    raw = h["winnings"]
    adj, st = raw, all_in_street(h)
    if st is not None:
        adj = equity(h["hole"], h["bot_hole"], h["board"][:BOARD_AT[st]]) * 2 * STACK - STACK
    street, ks = raw, deals(h)
    for s, k in enumerate(ks, 1):
        before = equity(h["hole"], h["bot_hole"], h["board"][:0 if s == 1 else ks[s - 2]])
        after = equity(h["hole"], h["bot_hole"], h["board"][:k])
        street += pot_before_deal(h["action"], s) * (before - after)
    return raw, adj, st is not None, street, bool(ks)


def stats(rows):
    n = len(rows)
    out = {"hands": n}
    for name, i in (("raw", 0), ("adjusted", 1), ("street", 3)):
        xs = [x[i] for x in rows]
        tot = sum(xs)
        sd = statistics.stdev(xs) if n > 1 else 0.0
        mean = tot / n if n else 0.0
        hw = 1.96 * sd / math.sqrt(n) if n else 0.0
        out.update({f"{name}_chips": tot, f"{name}_bb100": mean, f"{name}_ci95": [mean - hw, mean + hw],
                    f"sd_{name}": sd})
    out["sd_ratio"] = out["sd_adjusted"] / out["sd_raw"] if out["sd_raw"] else 0.0
    out["sd_ratio_street"] = out["sd_street"] / out["sd_raw"] if out["sd_raw"] else 0.0
    out["n_adjusted"] = sum(x[2] for x in rows)
    out["n_street_adjusted"] = sum(x[4] for x in rows)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    per, allrows = [], []
    for p in a.logs:
        with open(p) as f:
            hands = [json.loads(line) for line in f if line.strip()]
        prefetch(hands)
        rows = [score(h) for h in hands]
        per.append(dict(stats(rows), log=os.path.basename(p)))
        allrows += rows
    res = dict(stats(allrows), logs=per)
    for r in per + [res]:
        name = r.get("log", "TOTAL")
        if not r["hands"]:
            print(f"{name}: 0 hands")
            continue
        print(f"{name}: {r['hands']} hands, {r['n_adjusted']} adjusted")
        for k in ("raw", "adjusted", "street"):
            lo, hi = r[f"{k}_ci95"]
            print(f"  {k:8s} {r[f'{k}_chips']:12.1f} chips  {r[f'{k}_bb100']:9.2f} bb/100  "
                  f"[{lo:.2f}, {hi:.2f}]  sd {r[f'sd_{k}']:.1f}")
        print(f"  sd ratio (adjusted/raw) {r['sd_ratio']:.3f}, street {r['sd_ratio_street']:.3f}, "
              f"{r['n_street_adjusted']} street-adjusted")
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
