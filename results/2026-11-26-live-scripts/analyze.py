"""Per-match live-log analysis. Usage: python3 -I analyze.py LOG [LOG ...]  (or run.sh)"""
import sys, os, re, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opponent47 import Stats  # copy of chipzen/opponent.py at 47fcb67

TS = re.compile(r"^\d{4}-\d\d-\d\d [\d:,]+ (\S+) (\S+) (.*)$")
BAD = re.compile(r"illegal|error|invalid|reject|exception|traceback|timeout|fallback", re.I)
HISTE = re.compile(r"(\d+):(\w+):(-?\d+)(?::(\w+))?")


def kv(s):
    return dict(re.findall(r"(\w+)=(\S+)", s))


def parse_hist(s):
    return [dict(seat=int(a), action=b, amount=int(c), phase=d, ) for a, b, c, d in HISTE.findall(s)]


def contrib(hist):
    """Chips each seat put in: post/call add, bet/raise/all_in are street totals."""
    c = defaultdict(lambda: defaultdict(int))
    for e in hist:
        a, s, p = e["action"], e["seat"], e["phase"]
        if a.startswith("post") or a == "call":
            c[s][p] += e["amount"]
        elif a in ("raise", "bet", "all_in"):
            c[s][p] = max(c[s][p], e["amount"])
    return {s: sum(v.values()) for s, v in c.items()}


def new_match(name, commit, fname):
    return dict(name=name, commit=commit, file=fname, us=0, decs=[], hands={}, states={}, bad=[], boards={}, holes={})


def split_matches(path):
    ms, cur, commit = [], None, None
    for ln, line in enumerate(open(path, errors="replace"), 1):
        m = TS.match(line.rstrip("\n"))
        if not m:
            continue
        lg, lvl, msg = m.groups()
        if msg.startswith("pokercpp v") and "commit=" in msg:
            commit = msg.split('commit=')[0].replace('pokercpp ','').strip() + ' ' + msg.split('commit=')[1]
        if msg.startswith("match_start"):
            seats = eval(msg.split("seats=", 1)[1], {})
            cur = new_match("?", commit, os.path.basename(path)); cur["start"] = msg.split()[0][:0] + str(len(ms) + 1)
            for s in seats:
                if s[1]:
                    cur["us"] = s[0]
            for s in seats:
                if not s[1] and len(s) > 2:
                    cur["name"] = s[2]
            ms.append(cur); commit = None
            continue
        if cur is None:
            continue
        if lvl != "INFO" or (BAD.search(msg) and not msg.startswith(("STATE", "ROUND"))):
            cur["bad"].append(f"L{ln} {lvl} {msg[:120]}")
        if msg.startswith("STATE "):
            try:
                st = json.loads(msg[6:])
                h = st["hand_number"]
                cur["states"].setdefault(h, st)
                if len(st.get("board") or []) >= len(cur["boards"].get(h, [])):
                    cur["boards"][h] = st["board"] or []
                cur["holes"][h] = "".join(st.get("hole_cards") or [])
                if any(x.get("is_timeout") for x in st.get("action_history", [])):
                    cur["bad"].append(f"L{ln} is_timeout in hand {h}")
            except Exception as ex:
                cur["bad"].append(f"L{ln} bad STATE json {ex}")
        elif msg.startswith("hand=") and " phase=" in msg and "->" in msg:
            body, act = msg.split(" -> ", 1)
            d = kv(body)
            d["act"] = act.strip()
            cur["decs"].append(d)
            h = int(d["hand"])
            if d.get("board", "-") != "-":
                b = re.findall(r"[2-9TJQKA][cdhs]", d["board"])
                if len(b) >= len(cur["boards"].get(h, [])):
                    cur["boards"][h] = b
            cur["holes"][h] = d["hole"]
        elif msg.startswith("round_result "):
            d = kv(msg.split(" history=")[0])
            h = int(d["hand"])
            cur["hands"].setdefault(h, {})["hist"] = parse_hist(msg.split(" history=", 1)[1])
            cur["hands"][h]["winners"] = [int(x) for x in re.search(r"winners=\[([^\]]*)\]", msg).group(1).replace(" ", "").split(",") if x]
        elif msg.startswith("ROUND "):
            r = json.loads(msg[6:])
            cur["hands"].setdefault(r["hand_number"], {})["round"] = r
    return ms


def legal_check(d):
    """Flag chosen actions outside the legal set or out of raise bounds."""
    out = []
    legal = d["legal"].split(",")
    a = d["act"].split()
    if a[0] == "raise":
        if "raise" not in legal and "bet" not in legal:
            out.append("raise not legal")
        else:
            amt, lo, hi = int(a[1]), int(d["min_raise"]), int(d["max_raise"])
            if lo <= hi and not lo <= amt <= hi:
                out.append(f"raise {amt} outside [{lo},{hi}]")
    elif a[0] not in legal:
        out.append(f"{a[0]} not in legal {legal}")
    return out


def analyze(m):
    us, opp = m["us"], 1 - m["us"]
    hs = sorted(h for h in m["hands"] if "hist" in m["hands"][h])
    # starting stacks from first STATE
    h0 = hs[0]
    st = m["states"].get(h0)
    posted = sum(e["amount"] for e in m["hands"][h0]["hist"] if e["seat"] == us and e["action"].startswith("post"))
    start = {us: 10000, opp: 10000}
    if st:
        pos_o = sum(e["amount"] for e in m["hands"][h0]["hist"] if e["seat"] == opp and e["action"].startswith("post"))
        start = {us: st["your_stack"] + posted, opp: st["opponent_stacks"][0] + pos_o}
    stk = dict(start)
    stats, nets, opp_folds, notes = Stats(), {}, Counter(), []
    for h in hs:
        hd = m["hands"][h]
        hist = hd["hist"]
        bbs = [e["amount"] for e in hist if e["action"] == "post_big_blind"]
        bb = bbs[0] if bbs else 100
        dec = next((d for d in m["decs"] if int(d["hand"]) == h), None)
        if dec:
            bb = int(dec["bb"])
        eff = min(stk[us], stk[opp])
        stats.record_hand([dict(e) for e in hist], us, depth_bb=eff / bb, eff=eff)
        c = contrib(hist)
        w = hd["winners"]
        if "round" in hd:  # authoritative
            net = hd["round"]["stacks"][us] - stk[us]
        elif len(w) == 1:
            net = min(c.get(us, 0), c.get(opp, 0)) * (1 if w[0] == us else -1)
        else:
            net = 0
        nets[h] = net
        stk[us] += net
        stk[opp] -= net
        ofold = [e for e in hist if e["seat"] == opp and e["action"] == "fold"]
        if ofold:
            opp_folds[ofold[-1]["phase"]] += 1
        hd["bb"], hd["net"] = bb, net
    return dict(hs=hs, nets=nets, start=start, final=stk, opp_folds=opp_folds, stats=stats)


def fmt_hist(hist, us):
    return " ".join(f"{'U' if e['seat']==us else 'O'}:{e['action']}:{e['amount']}:{e['phase'][:2]}"
                    for e in hist)


def report(m):
    r = analyze(m)
    us = m["us"]
    n = len(r["hs"])
    won = r["final"][us] > r["final"][1 - us]
    print(f"=== {m['file']} | opp={m['name']} | commit={m['commit'] or 'none logged'}")
    print(f"hands={n}  result={'WON' if won else 'LOST'}  final stacks us={r['final'][us]} opp={r['final'][1-us]}  "
          f"(start {r['start'][us]}/{r['start'][1-us]})")
    illegal = [(d["hand"], x) for d in m["decs"] for x in legal_check(d)]
    print(f"decisions={len(m['decs'])}  illegal/legal-check flags={len(illegal)}  error-like log lines={len(m['bad'])}")
    for x in (illegal[:3] + [("-", b) for b in m["bad"][:3]]):
        print("   e.g.", x)
    mix = defaultdict(Counter)
    for d in m["decs"]:
        a = d["act"].split()
        k = a[0]
        if k == "raise":
            k = "allin" if int(a[1]) >= int(d["max_raise"]) else ("bet" if int(d["to_call"]) == 0 and d["phase"] != "preflop" else "raise")
        mix[d["phase"]][k] += 1
    for ph in ("preflop", "flop", "turn", "river"):
        if mix[ph]:
            print(f"   {ph:8s}", dict(sorted(mix[ph].items())), f"total {sum(mix[ph].values())}")
    agg = defaultdict(Counter)
    for k, v in r["stats"].counts.items():
        kk = k.split("@")[0] if k.split("@")[0] in ("first_in", "vs_open", "vs_shove") else k
        for o, x in v.items():
            agg[kk][o] += x
    for k in sorted(agg):
        tot = sum(agg[k].values())
        print(f"   {k:10s} n={tot}: " + ", ".join(f"{o} {x}" for o, x in agg[k].items() if x))
    of = r["opp_folds"]
    print(f"   opp ended hand by fold: {sum(of.values())} (preflop {of['preflop']}, flop {of['flop']}, turn {of['turn']}, river {of['river']})")
    print("   five biggest losses:")
    for h in sorted(r["hs"], key=lambda h: r["nets"][h])[:5]:
        hd = m["hands"][h]
        sd = ""
        if "round" in hd and hd["round"].get("showdown"):
            sd = " opp=" + "".join(next((s["hole_cards"] for s in hd["round"]["showdown"] if s["seat"] != us), []))
        print(f"    hand {h}: {r['nets'][h]:+d} chips bb={hd['bb']} hole={m['holes'].get(h, '?')} "
              f"board={''.join(m['boards'].get(h, [])) or '?'}{sd} | {fmt_hist(hd['hist'], us)}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        for m in split_matches(p):
            report(m)
            print()
