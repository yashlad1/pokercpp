#!/usr/bin/env python3
"""Per Slumbot match log: win or loss, and why each big hand (<= -20 bb) was lost (#189).

Each decision is judged against Slumbot's revealed hand (bot_hole).
Usage: python tools/slumbot_why.py [--out DIR] LOG [LOG ...]
"""
import argparse
import itertools
import json
import pathlib
import random

from pokerkit import StandardHighHand

DECK = [r + s for r in "23456789TJQKA" for s in "cdhs"]
BIG = -2000
MC_BOARDS = 5000


def _score(hole, opp, board):
    mine = StandardHighHand.from_game("".join(hole), "".join(board))
    his = StandardHighHand.from_game("".join(opp), "".join(board))
    return 1.0 if mine > his else 0.0 if mine < his else 0.5  # a split counts half


def true_equity(hole, opp, board):
    """Hole vs opp over every completion of board: exact for <= 2 to come, else 5000 seeded boards."""
    dead = {*hole, *opp, *board}
    deck = [c for c in DECK if c not in dead]
    need = 5 - len(board)
    if need <= 2:
        runs = [list(c) for c in itertools.combinations(deck, need)]
    else:
        rng = random.Random(0)
        runs = [rng.sample(deck, need) for _ in range(MC_BOARDS)]
    return sum(_score(hole, opp, board + r) for r in runs) / len(runs)


def judged(decisions):
    if decisions and decisions[-1]["sent"] == "f":
        return decisions[-1]
    puts = [d for d in decisions if d["sent"][0] in "cb"]
    return puts[-1] if puts else None


def explain(h, d):
    """(true_equity, required, cause, why) for one big loss."""
    if "bot_hole" not in h:
        return None, None, "unknown (cards not shown)", "Slumbot's cards were not shown."
    if d is None:
        return None, None, "blinds only", "Only blinds went in, no decision of ours put chips in."
    te = true_equity(h["hole"], h["bot_hole"], h["board"][:d["street"]])
    req = d["to_call"] / (d["pot"] + d["to_call"]) if d["to_call"] > 0 else 0.5
    facts = (f"{'/'.join(h['hole'])} vs his {'/'.join(h['bot_hole'])} on {d['street']} board cards: "
             f"{d['sent']} with true equity {te:.2f}, needed {req:.2f}")
    if d["sent"] == "f" and te >= req:
        cause = "folded the best hand"
    elif d["bluff"]:
        cause = "bluff called"
    elif te >= req:
        cause = "right decision, unlucky run-out"
    elif d["street"] == 0:
        cause = "preflop over-call"
    elif d["equity"] - te >= 0.25:
        cause = "overconfident vs his real hand"
    else:
        cause = "marginal decision lost"
    return te, req, cause, f"{cause}: {facts} (logged {d['equity']:.2f}, range {d['range']})."


def add(causes, cause, chips):
    c = causes.setdefault(cause, {"hands": 0, "chips": 0})
    c["hands"] += 1
    c["chips"] += chips


def ranked(causes):
    return dict(sorted(causes.items(), key=lambda kv: kv[1]["chips"]))


def analyse(path):
    hands = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    chips = sum(h["winnings"] for h in hands)
    big, causes = [], {}
    for i, h in enumerate(hands, 1):
        if h["winnings"] > BIG:
            continue
        d = judged(h["decisions"])
        te, req, cause, why = explain(h, d)
        row = {"hand": i, "chips": h["winnings"], "seat": "BB" if h["client_pos"] == 0 else "SB",
               "hole": h["hole"], "opp_hole": h.get("bot_hole"), "board": h["board"], "action": h["action"]}
        if d:
            row.update({k: d[k] for k in ("street", "sent", "to_call", "pot", "equity", "range")})
        row.update(true_equity=te, required=req, cause=cause, why=why)
        big.append(row)
        add(causes, cause, h["winnings"])
    return {"session": path.stem, "hands": len(hands), "chips": chips,
            "bb_per_100": chips / len(hands) if hands else 0.0,
            "result": "win" if chips > 0 else "loss" if chips < 0 else "even",
            "big_losses": big, "causes": ranked(causes)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    ap.add_argument("logs", nargs="+")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sessions, total = [], {}
    for p in a.logs:
        r = analyse(pathlib.Path(p))
        (out / f"{r['session']}.why.json").write_text(json.dumps(r, indent=1))
        sessions.append({k: r[k] for k in ("session", "result", "hands", "chips", "bb_per_100")})
        for c, v in r["causes"].items():
            total.setdefault(c, {"hands": 0, "chips": 0})
            total[c]["hands"] += v["hands"]
            total[c]["chips"] += v["chips"]
        print(f"{r['session']:40} {r['result']:5} {r['hands']:6} hands {r['chips']:9} chips "
              f"{r['bb_per_100']:8.1f} bb/100 big losses {len(r['big_losses'])}")
    summary = {"sessions": sessions, **{k: sum(s["result"] == r for s in sessions)
               for k, r in (("wins", "win"), ("losses", "loss"), ("evens", "even"))}, "causes": ranked(total)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print("\ncause                                   hands     chips")
    for c, v in summary["causes"].items():
        print(f"{c:38} {v['hands']:6} {v['chips']:9}")


if __name__ == "__main__":
    main()
