"""Paired comparison of two builds from `bench.py --dump` files.

    python tools/paired.py A.json B.json

Pair k is seed seed0 + k, played in both seat orders, so A and B saw the same
deals and the per-pair difference cancels the card luck. The interval is on
that difference, not on each build's interval against the opponent.
"""

import json
import math
import statistics
import sys


def bb100_ci(results, bb):
    """Same maths as bench.report: mean bb/100 and its 95% interval. Copied
    rather than imported so this stays standard library only."""
    n = len(results)
    hands = n * 2
    bb100 = (sum(results) / bb) / (hands / 100)
    se_pair = statistics.stdev(results) / math.sqrt(n)
    se = (se_pair * n / bb) / (hands / 100)
    return bb100, bb100 - 1.96 * se, bb100 + 1.96 * se


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python tools/paired.py A.json B.json")
    a, b = (json.load(open(p)) for p in sys.argv[1:])
    for k in ("seed0", "bb", "stack_bb", "opponent"):
        if a[k] != b[k]:
            sys.exit(f"cannot pair: {k} differs ({a[k]!r} vs {b[k]!r})")
    if len(a["results"]) != len(b["results"]):
        sys.exit(f"cannot pair: {len(a['results'])} pairs vs {len(b['results'])}")
    if len(a["results"]) < 2:
        sys.exit("cannot pair: need at least 2 pairs")
    bb = a["bb"]
    print(f"vs {a['opponent']}, {a['stack_bb']} bb deep, seed0 {a['seed0']}, "
          f"{2 * len(a['results'])} hands each")
    for name, d in (("A", a), ("B", b)):
        m, lo, hi = bb100_ci(d["results"], bb)
        print(f"  {name}: {m:+.1f} bb/100   95% CI [{lo:+.1f}, {hi:+.1f}]")
    diff = [x - y for x, y in zip(a["results"], b["results"])]
    m, lo, hi = bb100_ci(diff, bb)
    verdict = "better" if lo > 0 else ("worse" if hi < 0 else "inconclusive")
    print(f"A - B: {m:+.1f} bb/100   95% CI [{lo:+.1f}, {hi:+.1f}]   {verdict}")


main()
