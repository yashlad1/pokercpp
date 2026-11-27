"""Play the pokercpp bot against the public Slumbot API (issue #34).

The protocol follows Slumbot's public sample client (sample_api.py): POST JSON
to /slumbot/api/new_hand and /slumbot/api/act, action strings like "b200c/kk/kb400",
bet sizes are chips put in on that street only, 50/100 blinds, 200 bb stacks that
reset every hand. Plays anonymously with the session token the API returns (no
login). Uses urllib, so no extra dependency over the bench.

The hero is a bench.py agent driven through its View, built here from Slumbot's
state, so the decision code is the same code the bench exercises:
    --hero engine   PokerCpp (the engine directly)
    --hero bot      chipzen/bot.py, as the platform would drive it

Pacing: strictly sequential, one request at a time, 0.2 s pause between hands.
A failed request is retried at most twice (1 s, 2 s backoff), then the run stops
cleanly and keeps the hands already played. A server-rejected action stops the
run too (it is counted and reported, never retried).

Also runs in GitHub Actions (.github/workflows/slumbot.yml: twice a day plus on demand,
logs kept as artifacts only).

Usage:
    PYTHONPATH=chipzen python tools/slumbot.py --hands 500 --hero engine --log out.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bench  # also puts chipzen/ on sys.path
import pokercpp_engine
from pokerkit import StandardHighHand

HOST = "https://slumbot.com/slumbot/api"
SB, BB, STACK = 50, 100, 20000
PHASES = {0: "preflop", 1: "flop", 2: "turn", 3: "river"}
LAT = []


class Stop(Exception):
    pass


def post(path, data):
    """One JSON POST, retried at most twice. Raises Stop when it still fails."""
    err = None
    for attempt in range(3):
        if attempt:
            time.sleep(attempt)
        t = time.time()
        try:
            req = urllib.request.Request(
                f"{HOST}/{path}", json.dumps(data).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                out = json.load(r)
            LAT.append(time.time() - t)
            if "error_msg" in out:
                raise Stop(f"rejected: {out['error_msg']}")
            return out
        except Stop:
            raise
        except Exception as e:
            err = e
    raise Stop(f"request failed after retries: {err!r}")


def replay(action):
    """Walk Slumbot's action string (logic of the sample's ParseAction).
    Positions follow the API: 0 = big blind, 1 = small blind (acts first preflop)."""
    street, actor, prev = 0, 1, 0  # prev = chips each player put in on earlier streets
    bets, max_to, last, ends = [BB, SB], BB, BB - SB, False
    over, folder, events = None, None, []

    def end_street():
        nonlocal street, actor, prev, bets, max_to, last, ends, over
        prev += bets[0]
        bets, max_to, last, ends = [0, 0], 0, 0, False
        if street == 3:
            over = "showdown"
        else:
            street += 1
            actor = 0

    i = 0
    while i < len(action) and over is None:
        c = action[i]
        i += 1
        cap = STACK - prev
        if c == "/":
            continue
        if c == "k":
            events.append((actor, "k", 0, street, cap))
            if ends:
                end_street()
            else:
                actor, ends = 1 - actor, True
        elif c == "c":
            amt = bets[1 - actor] - bets[actor]
            bets[actor] = bets[1 - actor]
            events.append((actor, "c", amt, street, cap))
            last = 0
            if bets[actor] >= cap:
                over = "showdown"
            elif ends:
                end_street()
            else:
                actor, ends = 1 - actor, True
        elif c == "f":
            events.append((actor, "f", 0, street, cap))
            over, folder = "fold", actor
        elif c == "b":
            j = i
            while i < len(action) and action[i].isdigit():
                i += 1
            n = int(action[j:i])
            last, max_to = n - max_to, n
            bets[actor] = n
            events.append((actor, "b", n, street, cap))
            actor, ends = 1 - actor, True
        else:
            raise Stop(f"unparseable action {action!r}")
    cap = STACK - prev
    return dict(street=street, actor=actor, bets=bets, prev=prev, max_to=max_to, last=last,
                over=over, folder=folder, events=events, cap=cap,
                total=[prev + bets[0], prev + bets[1]])


def history(events, me_pos):
    """SDK-shaped history for the Bot agent; seat 0 is always the small blind."""
    seat = lambda p: 0 if p == 1 else 1
    h = [{"seat": 0, "action": "post_small_blind", "amount": SB, "phase": "preflop", "is_timeout": False},
         {"seat": 1, "action": "post_big_blind", "amount": BB, "phase": "preflop", "is_timeout": False}]
    for p, kind, amt, st, cap in events:
        a = {"k": "check", "c": "call", "f": "fold", "b": "raise"}[kind]
        if kind == "b" and amt >= cap or kind == "c" and amt >= cap:
            a = "all_in"
        h.append({"seat": seat(p), "action": a, "amount": amt, "phase": PHASES[st], "is_timeout": False})
    return h


def make_view(r, p, hand, me_pos):
    n, me = len(r["board"]), me_pos
    to_call = max(p["max_to"] - p["bets"][me], 0)
    cap = p["cap"]
    return bench.View(
        hole=r["hole_cards"], board=r["board"], pot=sum(p["total"]), to_call=to_call,
        min_raise=0 if p["max_to"] >= cap else min(cap, p["max_to"] + max(p["last"], BB)),
        max_raise=0 if p["max_to"] >= cap else cap,
        stack=STACK - p["total"][me], bb=BB,
        villain_raises=sum(1 for e in p["events"] if e[0] != me and e[1] == "b"),
        hand=hand, history=history(p["events"], me), seat=0 if me == 1 else 1,
        dealer_seat=0, opp_stack=STACK - p["total"][1 - me])


def to_incr(action, amount, v):
    """Map an agent's answer to Slumbot's notation, as bench.play_hand legalizes it.
    "raise to X" is already street-total, which is exactly Slumbot's bN."""
    if action == "raise" and v.max_raise > 0:
        return f"b{min(max(int(amount), v.min_raise), v.max_raise)}"
    if action == "fold" and v.to_call > 0:
        return "f"
    return "c" if v.to_call > 0 else "k"


def expected_winnings(r, p, me):
    """What the hand should pay us, from the action string and the revealed cards."""
    if p["over"] == "fold":
        return p["total"][1 - me] if p["folder"] != me else -p["total"][me]
    opp = r.get("bot_hole_cards")
    if not opp or len(r["board"]) != 5:
        return None
    b = "".join(r["board"])
    mine, theirs = (StandardHighHand.from_game("".join(r["hole_cards"]), b),
                    StandardHighHand.from_game("".join(opp), b))
    t = p["total"][me]
    return t if mine > theirs else -t if mine < theirs else 0


def play_hand(token, h, hero, rec):
    r = post("new_hand", {"token": token} if token else {})
    token = r.get("token") or token
    me = r["client_pos"]
    decisions = []
    while "winnings" not in r:
        p = replay(r["action"])
        if p["over"] or p["actor"] != me:
            raise Stop(f"unexpected state {r['action']!r}")
        v = make_view(r, p, h, me)
        rec.clear()
        action, amount = hero.act(v)
        incr = to_incr(action, amount, v)
        d = dict(rec)
        decisions.append({"street": len(v.board), "pot": v.pot, "to_call": v.to_call, "sent": incr,
                          "action": action, "amount": amount, "equity": d.get("equity"),
                          "range": d.get("range"), "bluff": d.get("bluff")})
        r = post("act", {"token": token, "incr": incr})
        token = r.get("token") or token
    p = replay(r["action"])
    exp = expected_winnings(r, p, me)
    if hasattr(hero, "hand_over"):
        seat = 0 if me == 1 else 1
        live = [{k: e[k] for k in ("seat", "action", "amount", "phase")} for e in history(p["events"], me)]
        for e in live:
            if e["action"] == "raise" or e["action"] == "all_in":
                e["action"] = "raise"
        showdown = ([{"seat": seat, "hole_cards": r["hole_cards"]}] +
                    [{"seat": 1 - seat, "hole_cards": r["bot_hole_cards"]}]
                    if p["over"] == "showdown" and r.get("bot_hole_cards") else [])
        w = r["winnings"]
        hero.hand_over({"hand_number": h + 1, "winner_seats": [seat] if w > 0 else [1 - seat] if w < 0 else [0, 1],
                        "pot": 2 * abs(w), "payouts": [], "showdown": showdown, "action_history": live,
                        "stacks": []}, seat)
    out = dict(action=r["action"], client_pos=me, hole=r["hole_cards"], bot_hole=r.get("bot_hole_cards"),
               board=r["board"], decisions=decisions, winnings=r["winnings"], expected=exp,
               showdown=p["over"] == "showdown")
    return token, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hands", type=int, default=100)
    ap.add_argument("--hero", choices=("engine", "bot"), default="engine")
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--log")
    ap.add_argument("--seed", type=int, default=0, help="offsets the hand ids that key our Monte Carlo seeds")
    a = ap.parse_args()

    hero = bench.PokerCpp(sims=a.sims) if a.hero == "engine" else bench.Bot(SB, BB, STACK, sims=a.sims)
    rec, inner = {}, pokercpp_engine.decide

    def tap(**kw):
        out = inner(**kw)
        rec.clear()
        rec.update(out)
        return out
    pokercpp_engine.decide = tap

    log = open(a.log, "w") if a.log else None
    t0, token, res, stop = time.time(), None, [], None
    vpip = pfr = sd = sdwin = mismatch = 0
    for h in range(a.hands):
        try:
            token, o = play_hand(token, a.seed * 1_000_000 + h, hero, rec)
        except Stop as e:
            stop = f"hand {h}: {e}"
            break
        res.append(o["winnings"])
        pre = [d["sent"] for d in o["decisions"] if d["street"] == 0]
        vpip += any(s.startswith("b") or s == "c" for s in pre)
        pfr += any(s.startswith("b") for s in pre)
        if o["showdown"]:
            sd += 1
            sdwin += o["winnings"] > 0
        if o["expected"] != o["winnings"]:
            mismatch += 1
            print(f"RECONCILE MISMATCH hand {h}: {o['action']} reported {o['winnings']} expected {o['expected']}",
                  file=sys.stderr)
        if log:
            log.write(json.dumps(o) + "\n")
            log.flush()
        if (h + 1) % 50 == 0:
            print(f"{h + 1} hands, {sum(res)} chips", flush=True)
        time.sleep(0.2)

    n = len(res)
    print(f"\nhands played: {n}" + (f"  (stopped: {stop})" if stop else ""))
    if n:
        mean = sum(res) / n
        se = statistics.stdev(res) / math.sqrt(n) if n > 1 else float("nan")
        print(f"total chips: {sum(res)}")
        print(f"bb/100: {mean / BB * 100:.1f}  95% CI [{(mean - 1.96 * se) / BB * 100:.1f}, {(mean + 1.96 * se) / BB * 100:.1f}]")
        print(f"VPIP {vpip / n:.1%} ({vpip}/{n}), preflop raise {pfr / n:.1%} ({pfr}/{n})")
        print(f"showdowns {sd}, won {sdwin} ({sdwin / sd:.1%})" if sd else "showdowns 0")
    print(f"rejected actions: {1 if stop and 'rejected' in stop else 0}; reconcile mismatches: {mismatch}")
    if LAT:
        s = sorted(LAT)
        print(f"requests {len(s)}, latency mean {sum(s) / len(s):.3f}s median {s[len(s) // 2]:.3f}s p95 {s[int(len(s) * .95)]:.3f}s")
    print(f"wall time: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
