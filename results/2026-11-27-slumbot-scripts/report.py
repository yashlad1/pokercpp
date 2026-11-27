"""Summarise tools/slumbot.py hand logs (JSONL, one hand per line).

Usage: python report.py LOG.jsonl [LOG2.jsonl ...]
Python stdlib only. client_pos 0 = big blind, 1 = small blind. Decision "street"
is the number of board cards (0 = preflop).
"""
import json
import math
import statistics
import sys

BB = 100


def ci(xs):
    n = len(xs)
    m = sum(xs) / n
    se = statistics.stdev(xs) / math.sqrt(n) if n > 1 else float("nan")
    return m / BB * 100, (m - 1.96 * se) / BB * 100, (m + 1.96 * se) / BB * 100


def pct(a, b):
    return f"{a}/{b} ({a / b:.1%})" if b else f"{a}/0"


def kind(sent):
    return "fold" if sent == "f" else "raise" if sent.startswith("b") else "call/check"


def main(paths):
    hands = [json.loads(l) for p in paths for l in open(p) if l.strip()]
    n = len(hands)
    if not n:
        sys.exit("no hands")
    w = [h["winnings"] for h in hands]
    print(f"hands {n}, chips {sum(w):+d}")
    m, lo, hi = ci(w)
    print(f"bb/100 {m:+.1f}  95% CI [{lo:+.1f}, {hi:+.1f}]  (per-hand SD {statistics.stdev(w):.0f} chips)")
    ex = [h["expected"] for h in hands if h.get("expected") is not None]
    if ex:
        m, lo, hi = ci(ex)
        print(f"expected-based ({len(ex)} hands) chips {sum(ex):+d}, bb/100 {m:+.1f}  95% CI [{lo:+.1f}, {hi:+.1f}]")
    pre = [[d["sent"] for d in h["decisions"] if d["street"] == 0] for h in hands]
    vpip = sum(any(s == "c" or s.startswith("b") for s in p) for p in pre)
    pfr = sum(any(s.startswith("b") for s in p) for p in pre)
    sd = [h for h in hands if h["showdown"]]
    print(f"VPIP {pct(vpip, n)}, preflop raise {pct(pfr, n)}, showdown wins {pct(sum(h['winnings'] > 0 for h in sd), len(sd))}")

    print("\nBy seat (chips per hand)")
    for name, pos in (("SB", 1), ("BB", 0)):
        x = [h["winnings"] for h in hands if h["client_pos"] == pos]
        if x:
            print(f"  {name}: {sum(x) / len(x):+.1f} ({len(x)} hands, {sum(x):+d} chips)")

    print("\nBy ending: hands (share), chips (per hand)")
    ends = {"we fold": [], "Slumbot folds": [], "showdown": []}
    for h in hands:
        ends["showdown" if h["showdown"] else "Slumbot folds" if h["winnings"] > 0 else "we fold"].append(h["winnings"])
    for k, x in ends.items():
        print(f"  {k}: {len(x)} ({len(x) / n:.0%}), {sum(x):+d}" + (f" ({sum(x) / len(x):+.1f})" if x else ""))

    print("\nPreflop lines")
    first = [h["decisions"][0]["sent"] for h in hands if h["decisions"] and h["decisions"][0]["street"] == 0]
    print(f"  first action a fold: {pct(sum(s == 'f' for s in first), len(first))}")

    def tally(label, sents):
        c = {"call/check": 0, "fold": 0, "raise": 0}
        for s in sents:
            c[kind(s)] += 1
        print(f"  {label}: called {c['call/check']}, folded {c['fold']}, re-raised {c['raise']} (of {len(sents)})")

    def pre_d(h):
        return [d["sent"] for d in h["decisions"] if d["street"] == 0]
    tally("BB facing Slumbot's open", [pre_d(h)[0] for h in hands
                                       if h["client_pos"] == 0 and h["action"].startswith("b") and pre_d(h)])
    tally("SB facing a 3-bet after our raise", [pre_d(h)[1] for h in hands
                                                if h["client_pos"] == 1 and len(pre_d(h)) > 1 and pre_d(h)[0].startswith("b")])
    tally("SB limp, then facing a raise", [pre_d(h)[1] for h in hands
                                           if h["client_pos"] == 1 and len(pre_d(h)) > 1 and pre_d(h)[0] == "c"])

    print("\nShowdown calibration (our last decision's equity)")
    bins = [("<0.5", 0, .5), ("0.5-0.6", .5, .6), ("0.6-0.7", .6, .7), ("0.7-0.8", .7, .8), ("0.8+", .8, 9)]
    for name, a, b in bins:
        x = [h for h in sd if (e := last_eq(h)) is not None and a <= e < b]
        if x:
            print(f"  {name}: {len(x)} hands, {sum(h['winnings'] > 0 for h in x)} wins ({sum(h['winnings'] > 0 for h in x) / len(x):.0%}), "
                  f"{sum(h['winnings'] for h in x):+d} chips")

    print("\nBiggest 5 losing hands")
    for h in sorted(hands, key=lambda h: h["winnings"])[:5]:
        d = h["decisions"][-1] if h["decisions"] else {}
        print(f"  {h['winnings']:+d}  {h['action']}  seat {'SB' if h['client_pos'] else 'BB'}  ours {' '.join(h['hole'])}  "
              f"Slumbot {' '.join(h['bot_hole'] or []) or '-'}  board {' '.join(h['board']) or '-'}  "
              f"last range {d.get('range')} equity {d.get('equity')}")


def last_eq(h):
    for d in reversed(h["decisions"]):
        if d.get("equity") is not None:
            return d["equity"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
