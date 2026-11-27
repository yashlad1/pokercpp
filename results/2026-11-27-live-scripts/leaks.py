# usage (repo root): python3 -I results/2026-11-27-live-scripts/leaks.py LOG...   (issue 176 leak metrics; uses 2026-11-26-live-scripts/analyze.py)
import sys, os, re, statistics as st
from collections import defaultdict, Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2026-11-26-live-scripts"))
import analyze as A
import glob
logs = sorted(p for a in sys.argv[1:] for p in glob.glob(a))
AGG = ("raise", "bet", "all_in")
def P(n, d): return f"{n}/{d} ({100*n/d:.0f}%)" if d else f"{n}/0"
M = []
for p in logs:
    for m in A.split_matches(p):
        r = A.analyze(m); m["r"] = r; M.append(m)
# per-hand rows
rows = []
for mi, m in enumerate(M):
    r = m["r"]; us = m["us"]; stk = r["start"][us]
    for h in r["hs"]:
        hd = m["hands"][h]; net = r["nets"][h]; hist = hd["hist"]; bb = hd["bb"]
        ds = [d for d in m["decs"] if int(d["hand"]) == h]
        c = A.contrib(hist); pot = sum(c.values())
        sd = bool(hd.get("round") and hd["round"].get("showdown"))
        row = dict(mi=mi, opp=m["name"], h=h, net=net, bb=bb, pot=pot / bb, ds=ds, hist=hist, sd=sd, stk0=stk, us=us)
        stk += net; rows.append(row)
def lastkind(d):
    a = d["act"].split()
    if a[0] == "raise":
        return "shove" if int(a[1]) >= int(d["max_raise"]) else ("bet/raise")
    return a[0]
print("== 1 chip flow by last decision type (pooled over %d matches, %d hands)" % (len(M), len(rows)))
flow = defaultdict(lambda: [0, 0])
for x in rows:
    if not x["ds"]: continue
    d = x["ds"][-1]; k = lastkind(d)
    for key in [(k, "ALL", "ALL"), (k, d["phase"], "ALL"), (k, "ALL", "big" if x["pot"] > 20 else "small")]:
        flow[key][0] += 1; flow[key][1] += x["net"]
for k in sorted(flow): print(k, flow[k])
print("totals net all hands", sum(x["net"] for x in rows), "no-decision hands", sum(1 for x in rows if not x["ds"]))
print("-- per match net")
for mi, m in enumerate(M):
    t = [x for x in rows if x["mi"] == mi]
    print(mi, m["file"], m["name"], "hands", len(t), "net", sum(x["net"] for x in t), "final", m["r"]["final"][m["us"]])
print("-- big pot flow by match: kind net")
bm = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for x in rows:
    if x["ds"] and x["pot"] > 20:
        k = lastkind(x["ds"][-1]); b = bm[x["mi"]][k]; b[0] += 1; b[1] += x["net"]
for mi in bm: print(mi, M[mi]["name"], {k: tuple(v) for k, v in bm[mi].items()})
print("\n== 2 calibration, showdown, pot>20bb (equity at last decision)")
bk = [(0, .5), (.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)]
big = [x for x in rows if x["sd"] and x["pot"] > 20 and x["ds"]]
def calib(S, label):
    print(label, "n", len(S), "lost", sum(1 for x in S if x["net"] < 0), "mean eq (lost)", round(st.mean(float(x["ds"][-1]["equity"]) for x in S if x["net"] < 0), 3) if any(x["net"] < 0 for x in S) else "-", "mean eq all", round(st.mean(float(x["ds"][-1]["equity"]) for x in S), 3) if S else "-")
    for lo, hi in bk:
        B = [x for x in S if lo <= float(x["ds"][-1]["equity"]) < hi]
        if not B: continue
        w = sum(1 if x["net"] > 0 else .5 if x["net"] == 0 else 0 for x in B)
        print(f"  eq {lo}-{min(hi,1)}: n={len(B)} mean_eq={st.mean(float(x['ds'][-1]['equity']) for x in B):.3f} win_share={w/len(B):.3f} net={sum(x['net'] for x in B)}")
calib(big, "POOLED")
for mi in range(len(M)):
    S = [x for x in big if x["mi"] == mi]
    if S: calib(S, f"match {mi} {M[mi]['name']}")
# also all showdowns for contrast
calib([x for x in rows if x["sd"] and x["ds"]], "ALL showdowns any pot")
# split by whether last decision was call vs raise
for k in ("call", "bet/raise", "shove", "check"):
    S = [x for x in big if lastkind(x["ds"][-1]) == k]
    if S: calib(S, "big pot last=" + k)
print("\n== 4 stuck")
def oppraise_post(x):
    return any(e["seat"] != x["us"] and e["action"] in ("raise", "all_in") and e["phase"] != "preflop" for e in x["hist"])
st4 = [x for x in rows if x["ds"] and oppraise_post(x) and A.contrib(x["hist"]).get(x["us"], 0) > .5 * x["stk0"] and lastkind(x["ds"][-1]) != "fold"]
w = sum(1 for x in st4 if x["net"] > 0)
print("half-stack after opp postflop raise: n", len(st4), "won", w, "net", sum(x["net"] for x in st4))
for x in st4: print("  ", M[x["mi"]]["name"], "h", x["h"], x["net"], "sd" if x["sd"] else "")
cd = []
for x in rows:
    ph = {d["phase"] for d in x["ds"] if d["phase"] != "preflop" and d["act"].split()[0] == "call"}
    if len(ph) >= 2: cd.append(x)
print("call-downs (calls on >=2 postflop streets): n", len(cd), "won", sum(1 for x in cd if x["net"] > 0), "lost", sum(1 for x in cd if x["net"] < 0), "net", sum(x["net"] for x in cd), "showdown", sum(1 for x in cd if x["sd"]))
cd3 = [x for x in cd if len({d["phase"] for d in x["ds"] if d["act"].split()[0] == "call" and d["phase"] != "preflop"}) == 3]
print("  calls on all 3 streets n", len(cd3), "net", sum(x["net"] for x in cd3))
print("  mean eq at last decision in call-downs", round(st.mean(float(x["ds"][-1]["equity"]) for x in cd), 3))
print("\n== 5 flop folds facing bet, small pot (pot before bet <=10bb)")
fo = defaultdict(lambda: [0, 0, 0, []])
for x in rows:
    for d in x["ds"]:
        if d["phase"] == "flop" and int(d["to_call"]) > 0 and (int(d["pot"]) - int(d["to_call"])) <= 10 * x["bb"]:
            f = fo[x["opp"]]; f[0] += 1
            if d["act"].split()[0] == "fold":
                f[1] += 1; f[2] += x["net"]; f[3].append((float(d["equity"]), float(d["required"])))
tot = [0, 0, 0]
for o, f in sorted(fo.items()):
    print(o, "facing", f[0], "fold", P(f[1], f[0]), "chips lost", f[2]); tot[0] += f[0]; tot[1] += f[1]; tot[2] += f[2]
allf = [e for f in fo.values() for e in f[3]]
print("TOTAL facing", tot[0], "fold", P(tot[1], tot[0]), "chips", tot[2], "mean eq at fold", round(st.mean(a for a, b in allf), 3), "mean required", round(st.mean(b for a, b in allf), 3))
print("\n== 6 preflop SB")
sb = Counter(); lim = [0, 0, 0, 0]
for x in rows:
    if any(e["seat"] == x["us"] and e["action"] == "post_small_blind" for e in x["hist"]):
        a = next((e for e in x["hist"] if e["seat"] == x["us"] and e["phase"] == "preflop" and not e["action"].startswith("post")), None)
        if not a: continue
        k = "raise" if a["action"] in AGG else "limp" if a["action"] == "call" else a["action"]
        sb[k] += 1
        if k == "limp": lim[0] += 1; lim[1] += x["net"]; lim[2] += x["net"] > 0; lim[3] += x["net"] < 0
print(dict(sb), "limp hands n,net,won,lost", lim)
for ph in ("preflop", "flop", "turn", "river"): pass
lim_rows = [x for x in rows if any(e["seat"] == x["us"] and e["action"] == "post_small_blind" for e in x["hist"]) and next((e["action"] for e in x["hist"] if e["seat"] == x["us"] and not e["action"].startswith("post")), None) == "call"]
fl = Counter()
for x in lim_rows:
    last = x["ds"][-1] if x["ds"] else None
    fl[last["phase"] + ":" + lastkind(last)] += 1
print("limp-hand end", dict(fl))
print("SB raise hands net", sum(x["net"] for x in rows if any(e["seat"]==x["us"] and e["action"]=="post_small_blind" for e in x["hist"]) and next((e["action"] for e in x["hist"] if e["seat"]==x["us"] and not e["action"].startswith("post")), None) in AGG))
print("BB hands net", sum(x["net"] for x in rows if any(e["seat"]==x["us"] and e["action"]=="post_big_blind" for e in x["hist"])), "SB hands net", sum(x["net"] for x in rows if any(e["seat"]==x["us"] and e["action"]=="post_small_blind" for e in x["hist"])))
print("\n== 7 latency")
TS = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d):(\d\d):(\d\d),(\d+) ")
def sec(l):
    m = TS.match(l); return int(m[2]) * 3600 + int(m[3]) * 60 + int(m[4]) + int(m[5]) / 1000 if m else None
allc, alln = [], []
for p in logs:
    cur = None; lastS = None; pend = None; res = {}
    for l in open(p, errors="replace"):
        t = sec(l)
        if t is None: continue
        if "match_start" in l:
            cur = len(res); res[cur] = ([], []); lastS = pend = None; continue
        if cur is None: continue
        if pend is not None:
            res[cur][1].append(t - pend); pend = None
        if " STATE " in l: lastS = t
        elif " hand=" in l and "->" in l:
            if lastS is not None: res[cur][0].append(t - lastS)
            lastS = None; pend = t
    for k, (c, n) in res.items():
        allc += c; alln += n
        print(os.path.basename(p), k, "n", len(c), "think med %.3f max %.3f" % (st.median(c), max(c)), "| decision->next line med %.3f max %.3f" % (st.median(n) if n else 0, max(n) if n else 0))
print("POOLED think med %.3f max %.3f; next med %.3f max %.3f" % (st.median(allc), max(allc), st.median(alln), max(alln)))
print("\n== 8 opponent styles")
S = defaultdict(lambda: Counter())
for x in rows:
    o = x["opp"]; us = x["us"]; hist = x["hist"]; opp = 1 - us
    pre = [e for e in hist if e["phase"] == "preflop"]
    if any(e["seat"] == opp and e["action"] == "post_small_blind" for e in pre):
        a = next((e for e in pre if e["seat"] == opp and not e["action"].startswith("post")), None)
        if a: S[o]["fi_n"] += 1; S[o]["fi_raise"] += a["action"] in AGG
    aggr = [e["seat"] for e in pre if e["action"] in AGG]
    fl = [e for e in hist if e["phase"] == "flop"]
    if aggr and aggr[-1] == opp and fl:
        for i, e in enumerate(fl):
            if e["seat"] == opp:
                S[o]["cb_n"] += 1; S[o]["cb_bet"] += e["action"] in AGG; break
            if e["action"] in AGG: break
    for i, e in enumerate(hist):
        if e["seat"] == us and e["action"] in AGG and e["phase"] != "preflop":
            n = next((y for y in hist[i + 1:] if y["seat"] == opp), None)
            if n and n["phase"] == e["phase"]:
                S[o]["fb_n"] += 1; S[o]["fb_fold"] += n["action"] == "fold"
for o in sorted({m["name"] for m in M}):
    s = S[o]; nets = sum(x["net"] for x in rows if x["opp"] == o); hands = sum(1 for x in rows if x["opp"] == o)
    print(o, "hands", hands, "net", nets, "| first_in raise", P(s["fi_raise"], s["fi_n"]), "| cbet", P(s["cb_bet"], s["cb_n"]), "| fold-to-our-postflop-bet", P(s["fb_fold"], s["fb_n"]))

print("\n== extra")
hi=[x for x in big if float(x["ds"][-1]["equity"])>=.6]
w=sum(1 if x["net"]>0 else .5 if x["net"]==0 else 0 for x in hi)
print("big pot eq>=0.6: n",len(hi),"mean eq %.3f"%st.mean(float(x["ds"][-1]["equity"]) for x in hi),"win share %.3f"%(w/len(hi)),"net",sum(x["net"] for x in hi))
hi=[x for x in big if float(x["ds"][-1]["equity"])>=.7]
w=sum(1 if x["net"]>0 else .5 if x["net"]==0 else 0 for x in hi)
print("big pot eq>=0.7: n",len(hi),"mean eq %.3f"%st.mean(float(x["ds"][-1]["equity"]) for x in hi),"win share %.3f"%(w/len(hi)),"net",sum(x["net"] for x in hi))
rg=Counter()
for x in rows:
    for d in x["ds"]:
        if d["phase"]=="flop" and int(d["to_call"])>0 and int(d["pot"])-int(d["to_call"])<=10*x["bb"] and d["act"].split()[0]=="fold": rg[d["range"]]+=1
print("range at small-pot flop folds",dict(rg))
rg=Counter()
for x in rows:
    for d in x["ds"]:
        if d["phase"]=="flop" and int(d["to_call"])>0 and int(d["pot"])-int(d["to_call"])<=10*x["bb"]: rg[d["range"]]+=1
print("range at all small-pot flop facing bet",dict(rg))
# BB: opp preflop raise -> our response
bbr=Counter(); bbn=Counter()
for x in rows:
    if any(e["seat"]==x["us"] and e["action"]=="post_big_blind" for e in x["hist"]):
        pre=[e for e in x["hist"] if e["phase"]=="preflop"]
        if any(e["seat"]!=x["us"] and e["action"] in AGG for e in pre):
            a=next(e for e in pre if e["seat"]==x["us"] and not e["action"].startswith("post")) if any(e["seat"]==x["us"] and not e["action"].startswith("post") for e in pre) else None
            k=a["action"] if a else "none"; bbr[k]+=1; bbn[k]+=x["net"]
print("BB vs opp raise: ",dict(bbr),dict(bbn))

print("\n== big-pot 0.5-0.6 hands")
for x in big:
    e=float(x["ds"][-1]["equity"])
    if .5<=e<.6: print(M[x["mi"]]["file"][-10:], "h", x["h"], x["net"], "range", x["ds"][-1]["range"], "eq", e, lastkind(x["ds"][-1]))
