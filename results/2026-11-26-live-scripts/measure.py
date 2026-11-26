"""Three measurements. python3 -I measure.py LOG... """
import sys, os, re, glob
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..") + "/"  # repo root
RK = {"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
rk = lambda c: RK.get(c[0]) or int(c[0])
ranked = []  # (high, low, suited, combos, cum_before)
cum = 0
for hi, lo, su, cb in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(true|false)\s*,\s*(\d+)\},", open(ROOT + "montecarlo/preflop_ranks.h").read()):
    ranked.append((int(hi), int(lo), su == "true", int(cb), cum)); cum += int(cb)
assert len(ranked) == 169 and cum == 1326
def locate(cards):
    a, b = sorted((rk(cards[0]), rk(cards[1])), reverse=True)
    su = cards[0][1] == cards[1][1] and a != b
    for h in ranked:
        if h[:3] == (a, b, su): return h
def inside(h, rng):  # engine rule: villainCombos
    if rng >= 1.0: return True
    wanted = int(max(rng, 0.01) * 1326 + 0.5)
    return h[4] < wanted
def pct(n, d): return f"{n} ({100*n/d:.0f}%)" if d else f"{n} (-)"
def tag(m): return f"{m['file'][:16]}#{m['start']} {m['name']} {(m['commit'] or 'none').split()[-1]}"
sd = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # tag -> (res,in/out) -> [n, chips]
real = defaultdict(Counter)
lost, cb, fb, sbf = [], defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
for p in sys.argv[1:]:
    for m in A.split_matches(p):
        r = A.analyze(m); us = m["us"]; t = tag(m)
        for d in m["decs"]:  # preflop realization = realized/equity on preflop decisions facing a bet
            if d["phase"] == "preflop" and int(d["to_call"]) > 0 and float(d["equity"]) > 0.05:
                real[t][round(float(d["realized"]) / float(d["equity"]), 2)] += 1
        for h in r["hs"]:
            hd = m["hands"][h]; net = r["nets"][h]; hist = hd["hist"]
            rd = hd.get("round")
            if rd and rd.get("showdown"):
                o = next((s for s in rd["showdown"] if s["seat"] != us), None)
                ds = [d for d in m["decs"] if int(d["hand"]) == h]
                if o and o.get("hole_cards") and ds:
                    rng = float(ds[-1]["range"]); loc = locate(o["hole_cards"]); ins = inside(loc, rng)
                    res = "lost" if net < 0 else "won" if net > 0 else "split"
                    for k in (t, "POOLED all", "POOLED 0eff667" if "0eff667" in t else None):
                        if k: x = sd[k][(res, "in" if ins else "out")]; x[0] += 1; x[1] += net
                    if res == "lost":
                        lost.append((t, h, rng, "".join(o["hole_cards"]), (loc[4] + loc[3] / 2) / 1326, net))
            pre = [e for e in hist if e["phase"] == "preflop"]
            fl = [e for e in hist if e["phase"] == "flop"]
            aggs = [e["seat"] for e in pre if e["action"] in ("raise", "bet", "all_in")]
            def nxt(i): return next((x for x in fl[i + 1:] if x["seat"] == us), None)
            cbet_done = False
            for i, e in enumerate(fl):
                if e["seat"] != us and e["action"] in ("raise", "bet", "all_in"):
                    n = nxt(i)
                    if n:
                        c = "raise" if n["action"] in ("raise", "all_in") else n["action"]
                        fb[t][c] += 1
                        if not cbet_done and aggs and aggs[-1] != us and not any(x["action"] in ("raise", "bet", "all_in") for x in fl[:i]):
                            cb[t][c] += 1
                    cbet_done = True
                    break
            else:
                pass
            # facing any bet: count each opp flop aggression event separately
            if any(e["phase"] == "preflop" and e["action"] == "post_small_blind" and e["seat"] == us for e in hist):
                a = next((e for e in pre if e["seat"] == us and not e["action"].startswith("post")), None)
                if a: sbf[t]["raise" if a["action"] in ("raise", "all_in") else "limp" if a["action"] == "call" else a["action"]] += 1
print("1. showdown range coverage (n, chips)  engine rule: top fraction counted in COMBOS, classes taken in order until cumulative combos >= round(range*1326); the class crossing the cut is inside; range=1.0 = everyone")
for t, d in sd.items():
    print(t, {f"{r}/{w}": f"{v[0]} / {v[1]:+d}" for (r, w), v in sorted(d.items())})
print("lost showdowns: match hand range opp pctile chips")
for l in lost: print("  %s h%d range=%.2f opp=%s pct=%.0f%% %+d" % (l[0], l[1], l[2], l[3], 100 * l[4], l[5]))
print("2. opp flop c-bet (last pre aggressor, first flop bet) -> our response; and facing the first opp flop bet of any kind")
for t in cb.keys() | fb.keys():
    n = sum(cb[t].values()); f = sum(fb[t].values())
    print(t, "cbet:", {k: pct(v, n) for k, v in cb[t].items()}, f"n={n} | any flop bet fold:", pct(fb[t]["fold"], f), "call", fb[t]["call"], "raise", fb[t]["raise"])
print("3. our SB first action")
for t, c in sbf.items(): print(t, {k: pct(v, sum(c.values())) for k, v in c.items()})
print("4. preflop realization (realized/equity, preflop, facing a bet): ratio -> decisions")
for t, c in real.items(): print(t, dict(sorted(c.items())), "n=%d" % sum(c.values()))
