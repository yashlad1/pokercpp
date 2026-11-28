#!/usr/bin/env python3
"""Black-box tests for tools/slumbot_report.py on a hand-built session log.

Every expected number below comes from a hand calculation written beside it.
Blinds 50/100, so bb/100 = chips / hands. client_pos 0 = big blind, 1 = small blind.
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent / "slumbot_report.py"

FLOP = ["2c", "7d", "Js"]
FULL = ["2c", "7d", "Js", "9h", "Kc"]


def dec(street, sent, equity):
    action = {"c": "call", "f": "fold", "k": "check"}.get(sent, "raise")
    return {"street": street, "pot": 300, "to_call": 0, "sent": sent, "action": action,
            "amount": 0, "equity": equity, "range": 0.5, "bluff": False}


def hand(action, pos, win, decs, showdown=False, board=()):
    return {"action": action, "client_pos": pos, "hole": ["As", "Ad"], "bot_hole": ["Qh", "Qd"],
            "board": list(board), "decisions": decs, "winnings": win, "expected": win,
            "showdown": showdown}


# Log A: 5 hands, -700 chips.
LOG_A = [
    # 1 BB, Slumbot opens, we call, fold to a flop bet. -200. we fold.
    hand("b200c/kb100f", 0, -200, [dec(0, "c", .4), dec(3, "k", .3), dec(3, "f", .2)], False, FLOP),
    # 2 BB, fold to the open. -100. we fold.
    hand("b200f", 0, -100, [dec(0, "f", .2)]),
    # 3 SB, we raise, Slumbot 3-bets, we call, split. 0. showdown, last equity 0.74.
    hand("b250b750c/kk/kk/kk", 1, 0, [dec(0, "b250", .6), dec(0, "c", .7), dec(5, "k", .74)], True, FULL),
    # 4 SB, limp, Slumbot raises, we fold. -100. we fold.
    hand("cb300f", 1, -100, [dec(0, "c", .4), dec(0, "f", .3)]),
    # 5 SB, limp, Slumbot raises, we call, showdown loss. -300. last equity 0.45.
    hand("cb300c/kk/kk/kk", 1, -300, [dec(0, "c", .4), dec(0, "c", .45), dec(5, "k", .45)], True, FULL),
]
# Log B: 6 hands, +650 chips.
LOG_B = [
    # 6 BB, Slumbot opens, we 3-bet, Slumbot calls, showdown win. +600. last equity 0.85.
    hand("b200b600c/kk/kk/kk", 0, 600, [dec(0, "b600", .8), dec(5, "k", .85)], True, FULL),
    # 7 SB, we raise, Slumbot folds. +100.
    hand("b250f", 1, 100, [dec(0, "b250", .6)]),
    # 8 BB, Slumbot opens, we call, showdown loss. -200. last equity 0.55.
    hand("b225c/kk/kk/kk", 0, -200, [dec(0, "c", .5), dec(5, "k", .55)], True, FULL),
    # 9 BB, fold to the open. -100. we fold.
    hand("b300f", 0, -100, [dec(0, "f", .2)]),
    # 10 SB, we raise, Slumbot calls, showdown win. +200. last equity 0.65.
    hand("b200c/kk/kk/kk", 1, 200, [dec(0, "b200", .6), dec(5, "k", .65)], True, FULL),
    # 11 BB, Slumbot folds the small blind before we act. +50. no decisions.
    hand("f", 0, 50, []),
]


def write(d, name, hands):
    p = pathlib.Path(d) / name
    p.write_text("".join(json.dumps(h) + "\n" for h in hands))
    return str(p)


def report(*logs):
    r = subprocess.run([sys.executable, str(TOOL), *logs], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def run_ab():
    with tempfile.TemporaryDirectory() as d:
        rc, out = report(write(d, "a.jsonl", LOG_A), write(d, "b.jsonl", LOG_B))
    assert rc == 0, out
    return out


def line(out, *words):
    """The one output line containing all the words (case-insensitive)."""
    # Wording tolerance: "big blind"/"BB", "small blind"/"SB", "below 0.5"/"<0.5".
    norm = lambda t: t.lower().replace("big blind", "bb").replace("small blind", "sb").replace("below 0.5", "<0.5")
    hits = [norm(l) for l in out.splitlines() if all(norm(w) in norm(l) for w in words)]
    assert hits, f"no line with {words!r} in:\n{out}"
    return hits[0]


def nums(s):
    return [float(x.replace(",", "")) for x in re.findall(r"[-+]?\d[\d,]*\.?\d*", s)]


def test_headline_chips_and_bb100():
    out = run_ab()
    # hands: 5 + 6 = 11. chips: -700 + 650 = -50. bb/100 = -50 / 11 = -4.545 -> -4.5.
    assert re.search(r"\b11\b", line(out, "hands")), out
    assert -50 in nums(line(out, "chips")), out
    assert -4.5 in nums(line(out, "bb/100")), out


def test_interval_95():
    out = run_ab()
    # sum of squares = 40000+10000+0+10000+90000+360000+10000+40000+10000+40000+2500 = 612500.
    # n*mean^2 = 50^2/11 = 227.27, so SS = 612272.7; sample variance = SS/10 = 61227.3,
    # sd = 247.44; SE = 247.44/sqrt(11) = 74.61; half width = 1.96*74.61 = 146.2.
    # interval = -4.5 -/+ 146.2 = [-150.8, +141.7].
    n = nums(line(out, "bb/100"))
    assert -150.8 in n and 141.7 in n, out


def test_vpip_pfr_showdown_wins():
    out = run_ab()
    # VPIP: hands 1,3,4,5,6,7,8,10 put chips in voluntarily = 8 of 11 (72.7%);
    # folds 2 and 9 (BB fold to open) and 11 (Slumbot folded, we never acted) do not.
    n = nums(line(out, "vpip"))
    assert 8 in n and 11 in n, out
    # preflop raise: hands 3, 6, 7, 10 = 4 of 11 (36.4%).
    n = nums(line(out, "raise", "11"))
    assert 4 in n, out
    # showdowns: 3,5,6,8,10 = 5. wins: 6 and 10 = 2; the split (hand 3) is not a win. 2 of 5 (40.0%).
    n = nums(line(out, "showdown", "win"))
    assert 2 in n and 5 in n, out


def test_seat_chips():
    out = run_ab()
    # SB hands 3,4,5,7,10: 0-100-300+100+200 = -100 over 5 hands = -20.0 per hand.
    n = nums(line(out, "sb", "5 hands"))
    assert -100 in n and 5 in n and -20 in n, out
    # BB hands 1,2,6,8,9,11: -200-100+600-200-100+50 = +50 over 6 hands = +8.3 per hand.
    n = nums(line(out, "bb", "6 hands"))
    assert 50 in n and 6 in n and 8.3 in n, out


def test_endings():
    out = run_ab()
    # we fold: hands 1,2,4,9 = 4 hands, -200-100-100-100 = -500.
    n = nums(line(out, "we fold"))
    assert 4 in n and -500 in n, out
    # Slumbot folds: hands 7 and 11 = 2 hands, +100+50 = +150.
    n = nums(line(out, "slumbot folds"))
    assert 2 in n and 150 in n, out
    # showdown: hands 3,5,6,8,10 = 5 hands, 0-300+600-200+200 = +300.
    n = nums(line(out, "showdown", "300"))
    assert 5 in n and 300 in n, out


def test_preflop_lines():
    out = run_ab()
    # BB facing an open: hands 1,8 call (2), hands 2,9 fold (2), hand 6 3-bet (1), of 5.
    # (hand 11 is Slumbot folding, not an open.)
    n = nums(line(out, "bb", "open"))
    assert n[-4:] == [2, 2, 1, 5] or (2 in n and 1 in n and 5 in n), out
    assert n.count(2) >= 2 and 5 in n, out
    # SB facing a 3-bet after our raise: hand 3 only, call 1, fold 0, re-raise 0, of 1.
    n = nums(line(out, "sb", "3-bet"))
    assert 1 in n and n.count(0) >= 2, out
    # SB limp then facing a raise: hand 4 fold, hand 5 call: called 1, folded 1, of 2.
    n = nums(line(out, "limp"))
    assert 1 in n and 2 in n, out


def test_calibration_buckets():
    out = run_ab()
    # Showdown hands by last decision equity (hands, wins, chips):
    # below 0.5: hand 5 (0.45)         -> 1, 0, -300
    # 0.5-0.6:   hand 8 (0.55)         -> 1, 0, -200
    # 0.6-0.7:   hand 10 (0.65), win   -> 1, 1, +200
    # 0.7-0.8:   hand 3 (0.74), split  -> 1, 0, 0   (a split is not a win)
    # 0.8+:      hand 6 (0.85), win    -> 1, 1, +600
    for label, wins, chips in [("<0.5", 0, -300), ("0.5-0.6", 0, -200),
                               ("0.6-0.7", 1, 200), ("0.7-0.8", 0, 0), ("0.8+", 1, 600)]:
        n = nums(line(out, label).split(label, 1)[1])
        assert n[0] == 1 and n[1] == wins and chips in n, (label, out)


def test_biggest_losses_include_the_tie():
    out = run_ab()
    # Losses sorted: -300 (5), -200 (1), -200 (8), -100 (2), -100 (4), -100 (9).
    # 5th worst is -100; hands 2, 4, 9 all tie at it, so 6 rows print.
    shown = ["cb300c/kk/kk/kk", "b200c/kb100f", "b225c/kk/kk/kk", "b200f", "cb300f", "b300f"]
    for a in shown:
        assert sum(a in l.split() for l in out.splitlines()) == 1, (a, out)
    # non-losses must not appear: split (hand 3), wins (6, 7, 10), the +50 hand.
    for a in ["b250b750c/kk/kk/kk", "b200b600c/kk/kk/kk", "b250f", "b200c/kk/kk/kk"]:
        assert not any(a in l.split() for l in out.splitlines()), (a, out)


def test_concatenates_logs():
    with tempfile.TemporaryDirectory() as d:
        rc, out = report(write(d, "a.jsonl", LOG_A))
    assert rc == 0, out
    # log A alone: 5 hands, -700 chips, so the two-log run above really joined them.
    assert re.search(r"\b5\b", line(out, "hands")), out
    assert -700 in nums(line(out, "chips")), out


def test_empty_log():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "empty.jsonl"
        p.write_text("")
        rc, out = report(str(p))
    assert rc == 0, out
    assert "Traceback" not in out, out
    assert re.search(r"\b0 hands\b", out), out


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(name)
            fn()
    print("ok")
