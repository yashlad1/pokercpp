"""Oracle log parser for #158 (written by the black-box tester, not the implementer).

Reads the `round_result hand=N ... history=seat:action:amount:phase,...` lines of a live
log and returns, per hand, the round-end history plus the effective stack and depth in bb
chained from the start stacks, the way the 24 Nov analysis did: both seats start at 10000,
and each hand's net is taken from its own history.

Net rule (derived here from the wire's amounts, not copied from anything): a post or a raise
sets the seat's commitment on that street to the amount (raise = street raise-to); a call
adds its amount (increment). The winner nets the smaller of the two total commitments, the
loser loses it, and a split pot nets zero.
"""
import re

LINE = re.compile(r" round_result hand=(\d+) .*?winners=\[([\d, ]*)\] history=(\S+)")


def entries(text):
    out = []
    for tok in text.split(","):
        s, a, amt, ph = tok.split(":")
        out.append({"seat": int(s), "action": a, "amount": int(amt), "phase": ph})
    return out


def commitments(hist):
    tot = [0, 0]
    for ph in ("preflop", "flop", "turn", "river"):
        c = [0, 0]
        for e in hist:
            if e["phase"] != ph:
                continue
            if e["action"] == "call":
                c[e["seat"]] += e["amount"]
            elif e["action"] in ("fold", "check"):
                pass
            else:  # posts, raise, bet, all_in: the amount is the street level
                c[e["seat"]] = e["amount"]
        tot[0] += c[0]
        tot[1] += c[1]
    return tot


def parse(path, start=10000):
    seen, hands = set(), []
    stacks = [start, start]
    for line in open(path):
        m = LINE.search(line)
        if not m or int(m.group(1)) in seen:
            continue
        n = int(m.group(1))
        seen.add(n)
        winners = [int(x) for x in m.group(2).replace(" ", "").split(",") if x]
        hist = entries(m.group(3))
        posts = [e["amount"] for e in hist if e["action"].startswith("post_")]
        bb = max(posts)
        eff = min(stacks)
        hands.append({"hand": n, "history": hist, "eff": eff, "depth_bb": eff / bb,
                      "start": list(stacks)})
        c = commitments(hist)
        pot = min(c)
        if len(winners) == 1:
            stacks[winners[0]] += pot
            stacks[1 - winners[0]] -= pot
    return hands, stacks
