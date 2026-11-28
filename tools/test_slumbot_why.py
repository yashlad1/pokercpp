#!/usr/bin/env python3
"""Black-box tests for tools/slumbot_why.py, on hand-built match logs (#189).

Run with an interpreter that has pokerkit. Every true_equity is derived by hand
in a comment next to the hand.
"""
import itertools
import json
import pathlib
import subprocess
import sys
import tempfile

from pokerkit import Card, StandardHighHand

TOOL = pathlib.Path(__file__).resolve().parent / "slumbot_why.py"


def dec(street, pot, to_call, sent, equity, rng=0.3, bluff=False):
    return {"street": street, "pot": pot, "to_call": to_call, "sent": sent,
            "action": {"k": "check", "c": "call", "f": "fold"}.get(sent, "raise"),
            "amount": 0, "equity": equity, "range": rng, "bluff": bluff}


def hand(winnings, decisions, hole, opp, board, pos=0, action="x"):
    h = {"action": action, "client_pos": pos, "hole": hole, "board": board,
         "decisions": decisions, "winnings": winnings, "expected": winnings, "showdown": True}
    if opp is not None:
        h["bot_hole"] = opp
    return h


# 1. folded the best hand. River: we hold As Ks, board Ah Kd: aces and kings two pair;
#    he holds Qc Qd, a lone pair of queens. The board is complete, so true_equity = 1.0 exactly. required = 1000 / (3000 + 1000) = 0.25 <= 1.0.
FOLDED = hand(-2500, [dec(5, 3000, 1000, "f", 0.9)], ["As", "Ks"], ["Qc", "Qd"],
              ["Ah", "Kd", "7c", "2s", "3h"], pos=1)

# 2. bluff called. River bet flagged bluff; we hold 8s 6s (ace-king high), he holds Ac Td
#    (pair of aces): we lose, true_equity = 0.0 exactly. required = 0.5 (to_call 0).
BLUFF = hand(-3000, [dec(5, 3000, 0, "b1500", 0.1, bluff=True)], ["8s", "6s"], ["Ac", "Td"],
             ["Ah", "Kd", "9c", "5h", "3d"])

# 3. right decision, unlucky run-out. Turn call; we hold Ks Kd (set of kings with Kc),
#    he holds Ah Qh on Kc 8h 5h 2d (flush draw). 44 unseen river cards.
#    His winning rivers: hearts not 2h (2h pairs the deuce, we make kings full of deuces
#    and beat his flush), not Kh (Kh gives us quads): the 13 hearts minus Ah Qh 8h 5h
#    Kh 2h leaves 3h 4h 6h 7h 9h Th Jh = 7 outs. Other rivers: we keep the best hand
#    (aces or queens pair him, nothing beats a set; 8x/5x/2x/Kx only help us).
#    true_equity = 37/44 = 0.840909. required = 500 / (2500 + 500) = 0.1667 <= 0.84.
#    The hand then lost on the river heart: board runs out to 7h.
UNLUCKY_BOARD = ["Kc", "8h", "5h", "2d", "7h"]
UNLUCKY = hand(-2000, [dec(4, 2500, 500, "c", 0.8)], ["Ks", "Kd"], ["Ah", "Qh"], UNLUCKY_BOARD)
UNLUCKY_EQ = 37 / 44

# 4. preflop over-call. We call an all-in (20000) holding KcKd, he holds AhAs.
#    KK vs AA is about 0.18 (well known: AA vs KK is 0.82).
#    required = 19900 / (20100 + 19900) = 0.4975 > 0.18.
OVERCALL = hand(-20000, [dec(0, 20100, 19900, "c", 0.55)], ["Kc", "Kd"], ["Ah", "As"],
                ["2c", "7d", "9s", "Jh", "3h"])

# 5. overconfident vs his real hand. River call at logged equity 0.8. We hold Ah Qc
#    (pair of aces, Ah+As); he holds 9h 9c (set of nines with 9d). He wins, so
#    true_equity = 0.0. required = 1000 / (4000 + 1000) = 0.2. 0.8 - 0.0 >= 0.25.
OVERCONF = hand(-5000, [dec(5, 4000, 1000, "c", 0.8)], ["Ah", "Qc"], ["9h", "9c"],
                ["As", "9d", "5c", "3h", "2s"])

# 6. marginal decision lost. River call at logged equity 0.2; we hold 8c 7c, he holds
#    Ah Qd (pair of aces over our ace-high): true_equity = 0.0. required =
#    1000 / (2000 + 1000) = 0.3333 > 0.0, street 5, and 0.2 - 0.0 < 0.25.
MARGINAL = hand(-2300, [dec(5, 2000, 1000, "c", 0.2)], ["8c", "7c"], ["Ah", "Qd"],
                ["Ac", "Kd", "4s", "3h", "2d"])

# 7. blinds only. Nothing but checks: no fold, no call, no bet.
BLINDS = hand(-2100, [dec(3, 400, 0, "k", 0.5)], ["8c", "7c"], ["Ah", "Qd"],
              ["Ac", "Kd", "4s", "3h", "2d"])

# 8. unknown (cards not shown): bot_hole absent.
UNKNOWN = hand(-2200, [dec(5, 2000, 1000, "c", 0.5)], ["8c", "7c"], None,
               ["Ac", "Kd", "4s", "3h", "2d"])

# Size threshold: exactly -2000 is listed (UNLUCKY above); -1999 is not.
SMALL_LOSS = hand(-1999, [dec(5, 2000, 1000, "c", 0.5)], ["8c", "7c"], ["Ah", "Qd"],
                  ["Ac", "Kd", "4s", "3h", "2d"])
WIN = hand(1500, [dec(5, 1000, 0, "b500", 0.9)], ["As", "Ks"], ["Qc", "Qd"],
           ["Ah", "Kd", "7c", "2s", "3h"])

LOSE_HANDS = [WIN, SMALL_LOSS, FOLDED, BLUFF, UNLUCKY, OVERCALL, OVERCONF, MARGINAL, BLINDS, UNKNOWN]
# 1-based line numbers of the big losses, by cause
LINE = {"folded": 3, "bluff": 4, "unlucky": 5, "overcall": 6, "overconf": 7,
        "marginal": 8, "blinds": 9, "unknown": 10}
WIN_HANDS = [dec_h for dec_h in (WIN, hand(500, [], ["2c", "3c"], ["4d", "5d"], []),
                                 hand(-200, [], ["2c", "3c"], ["4d", "5d"], []))]
EVEN_HANDS = [hand(100, [], ["2c", "3c"], ["4d", "5d"], []),
              hand(-100, [], ["2c", "3c"], ["4d", "5d"], [])]


def write_log(d, stem, hands):
    p = pathlib.Path(d) / f"{stem}.jsonl"
    p.write_text("".join(json.dumps(h) + "\n" for h in hands))
    return str(p)


def run(out, *logs):
    r = subprocess.run([sys.executable, str(TOOL), "--out", str(out), *logs],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def load(out, name):
    return json.loads((pathlib.Path(out) / name).read_text())


def setup(d):
    logs = [write_log(d, "lost", LOSE_HANDS), write_log(d, "won", WIN_HANDS),
            write_log(d, "even", EVEN_HANDS)]
    out = pathlib.Path(d) / "out"
    run(out, *logs)
    return out


def big(out, line):
    rows = [b for b in load(out, "lost.why.json")["big_losses"] if b["hand"] == line]
    assert len(rows) == 1, (line, rows)
    return rows[0]


def ranked(causes):
    """cause names, most chips lost first (accepts a list of rows or an ordered dict)."""
    rows = causes.items() if isinstance(causes, dict) else [(r["cause"], r) for r in causes]
    return [(n, r["hands"], abs(r["chips"])) for n, r in rows]


def test_session_results():
    with tempfile.TemporaryDirectory() as d:
        out = setup(d)
        lost, won, even = (load(out, f"{s}.why.json") for s in ("lost", "won", "even"))
        chips = sum(h["winnings"] for h in LOSE_HANDS)
        assert (lost["session"], lost["hands"], lost["chips"], lost["result"]) == \
            ("lost", 10, chips, "loss")
        assert abs(lost["bb_per_100"] - chips / 10) < 1e-9
        assert (won["hands"], won["chips"], won["result"]) == (3, 1800, "win")
        assert abs(won["bb_per_100"] - 600) < 1e-9
        assert (even["chips"], even["result"]) == (0, "even")
        assert won["big_losses"] == [] and even["big_losses"] == []


def test_summary():
    with tempfile.TemporaryDirectory() as d:
        out = setup(d)
        s = load(out, "summary.json")
        assert (s["wins"], s["losses"], s["evens"]) == (1, 1, 1)
        rows = {r["session"]: r for r in s["sessions"]}
        assert set(rows) == {"lost", "won", "even"}
        assert rows["won"]["result"] == "win" and rows["lost"]["result"] == "loss"
        assert rows["won"]["hands"] == 3 and rows["won"]["chips"] == 1800
        assert abs(rows["won"]["bb_per_100"] - 600) < 1e-9
        # most chips lost first; chips are the sum over that cause's big losses
        assert ranked(s["causes"]) == [
            ("preflop over-call", 1, 20000), ("overconfident vs his real hand", 1, 5000),
            ("bluff called", 1, 3000), ("folded the best hand", 1, 2500),
            ("marginal decision lost", 1, 2300), ("unknown (cards not shown)", 1, 2200),
            ("blinds only", 1, 2100), ("right decision, unlucky run-out", 1, 2000)]


def test_big_loss_threshold():
    with tempfile.TemporaryDirectory() as d:
        out = setup(d)
        got = sorted(b["hand"] for b in load(out, "lost.why.json")["big_losses"])
        # line 1 is a win, line 2 is -1999 (not listed), -2000 and below are listed
        assert got == sorted(LINE.values()), got
        lost = load(out, "lost.why.json")
        assert sum(c["hands"] for c in lost["causes"].values()) == 8 if isinstance(lost["causes"], dict) \
            else sum(c["hands"] for c in lost["causes"]) == 8


def test_folded_the_best_hand():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["folded"])
        assert b["cause"] == "folded the best hand"
        assert b["true_equity"] == 1.0
        assert abs(b["required"] - 0.25) < 1e-9
        assert (b["chips"], b["seat"], b["street"], b["sent"]) == (-2500, "SB", 5, "f")
        assert (b["to_call"], b["pot"], b["equity"]) == (1000, 3000, 0.9)
        assert b["hole"] == ["As", "Ks"] and b["opp_hole"] == ["Qc", "Qd"]
        assert b["board"] == ["Ah", "Kd", "7c", "2s", "3h"] and b["action"] == "x"
        assert isinstance(b["why"], str) and b["why"]


def test_bluff_called():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["bluff"])
        assert b["cause"] == "bluff called"
        assert b["true_equity"] == 0.0
        assert b["required"] == 0.5 and b["seat"] == "BB" and b["sent"] == "b1500"


def brute_turn_equity(hole, opp, board4):
    dead = {*hole, *opp, *board4}
    deck = [r + s for r in "23456789TJQKA" for s in "cdhs" if r + s not in dead]
    assert len(deck) == 44
    score = 0.0
    for c in deck:
        mine = StandardHighHand.from_game("".join(hole), "".join(board4) + c)
        his = StandardHighHand.from_game("".join(opp), "".join(board4) + c)
        score += 1.0 if mine > his else 0.5 if mine == his else 0.0
    return score / 44


def test_unlucky_runout():
    brute = brute_turn_equity(["Ks", "Kd"], ["Ah", "Qh"], UNLUCKY_BOARD[:4])
    assert abs(brute - UNLUCKY_EQ) < 1e-9, brute  # hand count agrees with the brute force
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["unlucky"])
        assert b["cause"] == "right decision, unlucky run-out"
        assert abs(b["true_equity"] - UNLUCKY_EQ) < 1e-6  # exact: only the river is to come
        assert abs(b["required"] - 500 / 3000) < 1e-9 and b["street"] == 4
        assert b["chips"] == -2000  # exactly -2000 is listed


def test_preflop_overcall():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["overcall"])
        assert b["cause"] == "preflop over-call"
        assert abs(b["true_equity"] - 0.18) <= 0.02
        assert abs(b["required"] - 19900 / 40000) < 1e-9 and b["street"] == 0


def test_overconfident():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["overconf"])
        assert b["cause"] == "overconfident vs his real hand"
        assert b["true_equity"] == 0.0 and b["equity"] == 0.8
        assert abs(b["required"] - 0.2) < 1e-9


def test_marginal():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["marginal"])
        assert b["cause"] == "marginal decision lost"
        assert b["true_equity"] == 0.0 and abs(b["required"] - 1 / 3) < 1e-9


def test_blinds_only():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["blinds"])
        assert b["cause"] == "blinds only" and b["chips"] == -2100


def test_unknown_cards_not_shown():
    with tempfile.TemporaryDirectory() as d:
        b = big(setup(d), LINE["unknown"])
        assert b["cause"] == "unknown (cards not shown)" and b["chips"] == -2200


def test_deterministic():
    with tempfile.TemporaryDirectory() as d:
        logs = [write_log(d, "lost", LOSE_HANDS), write_log(d, "won", WIN_HANDS)]
        texts = []
        for name in ("o1", "o2"):
            out = pathlib.Path(d) / name
            run(out, *logs)
            texts.append({p.name: p.read_text() for p in out.glob("*.json")})
        assert set(texts[0]) == {"lost.why.json", "won.why.json", "summary.json"}
        assert texts[0] == texts[1]


def test_prints_table():
    with tempfile.TemporaryDirectory() as d:
        r = run(pathlib.Path(d) / "out", write_log(d, "lost", LOSE_HANDS))
        assert "lost" in r.stdout and "loss" in r.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(name)
            fn()
    print("ok")
