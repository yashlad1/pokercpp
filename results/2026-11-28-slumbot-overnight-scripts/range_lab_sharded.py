"""Run range_lab.py (00f1fb4, PR #191) sharded over processes; pooled rates are computed once from all hands, so the totals equal a serial run.

Usage: python results/2026-11-28-slumbot-overnight-scripts/range_lab_sharded.py TOOLS_DIR "LOG_GLOB" OUT.json
"""
import sys, json, glob, multiprocessing
sys.path.insert(0, sys.argv.pop(1))
import range_lab as R
FIELDS = ("covered_hard_pct", "covered_weighted_pct", "covered_weighted_count_pct", "mean_log_score", "mean_log_score_hard")
def work(shard):
    return R.measure(shard)
if __name__ == "__main__":
    multiprocessing.set_start_method("fork")
    hands = [json.loads(l) for p in sorted(glob.glob(sys.argv[1])) for l in open(p) if l.strip()]
    allR = R.rates(hands)
    R.rates = lambda hs: allR
    k = 40
    shards = [hands[i::k] for i in range(k)]
    with multiprocessing.Pool(10) as pool:
        parts = pool.map(work, shards, chunksize=1)
    tot = {}
    for part in parts:
        for st, r in part.items():
            t = tot.setdefault(st, {"n": 0, **{f: 0.0 for f in FIELDS}})
            t["n"] += r["n"]
            for f in FIELDS:
                t[f] += r[f] * r["n"]
    out = {st: {"n": t["n"], **{f: t[f] / t["n"] for f in FIELDS}} for st, t in tot.items()}
    order = ["preflop", "flop", "turn", "river"]
    print(f"{'street':8}{'n':>6}{'hard %':>9}{'wtd mass %':>12}{'wtd count %':>13}{'wtd log':>9}{'hard log':>10}")
    for name in order:
        r = out[name]
        print(f"{name:8}{r['n']:>6}{r['covered_hard_pct']:>9.1f}{r['covered_weighted_pct']:>12.1f}"
              f"{r['covered_weighted_count_pct']:>13.1f}{r['mean_log_score']:>9.3f}{r['mean_log_score_hard']:>10.3f}")
    json.dump({"streets": out}, open(sys.argv[2], "w"), indent=1)
