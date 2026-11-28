"""Showdown calibration over many session logs: our last logged equity vs the share of showdowns won (split = half).

Usage: python results/2026-11-28-slumbot-overnight-scripts/calibration.py LOG [LOG ...]
"""
import json
import sys

hs = [json.loads(l) for p in sys.argv[1:] for l in open(p) if l.strip()]
sd = [h for h in hs if h["showdown"] and h["decisions"]]
won = lambda g: sum(1 if h["winnings"] > 0 else .5 if h["winnings"] == 0 else 0 for h in g) / len(g)
eq = lambda g: sum(h["decisions"][-1]["equity"] for h in g) / len(g)
for lo, hi in ((0, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
    g = [h for h in sd if lo <= h["decisions"][-1]["equity"] < hi]
    print(f"{lo}-{hi}: {len(g)} hands, mean logged {eq(g):.3f}, won {won(g):.3f}, chips {sum(h['winnings'] for h in g)}")
r = [h for h in sd if h["decisions"][-1]["street"] == 5 and h["decisions"][-1]["sent"] == "c" and h["decisions"][-1]["to_call"] > 0]
print(f"river call facing a bet: {len(r)} hands, mean logged {eq(r):.3f}, won {won(r):.3f}, chips {sum(h['winnings'] for h in r)}")
