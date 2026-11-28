#!/usr/bin/env python3
"""Black-box tests for tools/slumbot_luck.py on hand-built Slumbot logs.

Every expected number comes from a hand calculation written beside it. Blinds 50/100, stacks 20,000,
so bb/100 = chips / hands. A hand is adjusted only if both players were all-in, the last all-in bet was
called before the river, and bot_hole is known: adjusted = eq * pot - our contribution (pot = 40,000,
our contribution = 20,000 whenever both stacks are in). Every other hand: adjusted = winnings.
Run with an interpreter that has pokerkit (the brute-force cross-checks use it).

JSON field names are the tests' reading of the spec (the spec names fields but not keys):
hands, raw_chips, raw_bb100, raw_ci95 [lo, hi], adjusted_chips, adjusted_bb100, adjusted_ci95 [lo, hi],
sd_raw, sd_adjusted, sd_ratio (= sd_adjusted / sd_raw), n_adjusted, and "logs": one row per LOG, in CLI order.
"""
import itertools
import json
import math
import pathlib
import subprocess
import sys
import tempfile

from pokerkit import StandardHighHand

TOOL = pathlib.Path(__file__).resolve().parent / "slumbot_luck.py"
DECK = [r + s for r in "23456789TJQKA" for s in "cdhs"]


def hand(action, win, hole, bot, board, pos=0):
    return {"action": action, "client_pos": pos, "hole": list(hole), "bot_hole": list(bot),
            "board": list(board), "decisions": [], "winnings": win, "expected": win,
            "showdown": False}


def write(d, name, hands):
    p = pathlib.Path(d) / name
    p.write_text("".join(json.dumps(h) + "\n" for h in hands))
    return str(p)


def run(*logs, out_json=False):
    with tempfile.TemporaryDirectory() as d:
        paths = [write(d, f"{i}.jsonl", h) for i, h in enumerate(logs)]
        cmd = [sys.executable, str(TOOL), *paths]
        if out_json:
            cmd += ["--out", str(pathlib.Path(d) / "o.json")]
        r = subprocess.run(cmd, capture_output=True, text=True)
        js = json.loads((pathlib.Path(d) / "o.json").read_text()) if out_json and r.returncode == 0 else None
    return r.returncode, r.stdout + r.stderr, js


def result(*logs):
    rc, out, js = run(*logs, out_json=True)
    assert rc == 0, out
    return js


def brute_eq(hero, villain, board_now):
    """Our equity by enumerating every completion of the board (ties = half). pokerkit as the judge."""
    dead = set(hero + villain + board_now)
    rest = [c for c in DECK if c not in dead]
    k = 5 - len(board_now)
    score = n = 0
    for run_out in itertools.combinations(rest, k):
        b = "".join(board_now) + "".join(run_out)
        a = StandardHighHand.from_game("".join(hero), b)
        v = StandardHighHand.from_game("".join(villain), b)
        score += 1 if a > v else 0.5 if a == v else 0
        n += 1
    return score / n


# --- the hands -------------------------------------------------------------------------------------
# H_PRE: AA vs KK all-in preflop, KK wins. We lose 20,000. Equity of AA vs KK is about 81.8% (the
# standard preflop equity table, e.g. Poker Stove / Equilab: AA vs KK = 81.9% suit-averaged, 18.1% for KK).
# adjusted = 0.8176 * 40000 - 20000 = 32704 - 20000 = +12704.  Tolerance +-400 for the Monte Carlo.
H_PRE = hand("b20000c///", -20000, ["As", "Ah"], ["Kd", "Kc"], ["2h", "7s", "9c", "Ks", "3d"], 1)
PRE_ADJ = 0.8176 * 40000 - 20000

# H_FLOP: AsAh vs KcKd, flop 2d 7c 9h, all-in on the flop and called, two cards to come. Real run-out Kh 3s:
# the K gives them a set, we lose 20,000.
# 52 - 4 hole - 3 board = 45 cards, C(45,2) = 990 run-outs. No flush or straight is reachable by either side
# (best any side can do with 2 cards: 4 to a flush, 3 of 5 in a straight).
# They win when a K (Kh, Ks) comes and we do not also pair with an A (Ac, Ad):
#   run-outs with at least one K = 990 - C(43,2) = 990 - 903 = 87;
#   of those, K+A together (set of aces beats set of kings, or A+K board gives us trips A) = 2*2 = 4 -> we win;
#   so they win 87 - 4 = 83; we win the other 907; no ties.
# eq = 907/990. adjusted = 907/990 * 40000 - 20000 = 36646.4646 - 20000 = +16646.46.
H_FLOP = hand("b200c/b19800c//", -20000, ["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h", "Kh", "3s"])
FLOP_EQ = 907 / 990
FLOP_ADJ = FLOP_EQ * 40000 - 20000

# H_TURN: same hands, board 2d 7c 9h 4c, all-in on the turn and called, one card to come. Real river Kh.
# 52 - 4 - 4 = 44 rivers. They win only on Kh or Ks (set of kings): 2. We win the other 42
# (A makes us a set; a 2/7/9/4 pairs the board, KK or AA still two pair, AA higher). No flush (4 clubs at
# most for them: Kc 7c 4c + one more = 4 cards), no straight. No ties.
# eq = 42/44. adjusted = 42/44 * 40000 - 20000 = 38181.82 - 20000 = +18181.82.
H_TURN = hand("b200c/kk/b19800c/", -20000, ["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h", "4c", "Kh"])
TURN_EQ = 42 / 44
TURN_ADJ = TURN_EQ * 40000 - 20000

# H_SPLIT: we hold Ah Kd, they hold As Qc, board 2s 2h 7d 7c (two pair on the board, ace plays for both),
# all-in on the turn, called. Real river 9c: we split, winnings 0.
# 44 rivers: Ac, Ad (2): we have AA77 + K kicker, they AA77 + Q: we win.
#            Ks, Kh, Kc (3): we have KK77 + A, they have 7722 + A: we win.      -> 5 wins.
#            Qs, Qh, Qd (3): they have QQ77 + A, we have 7722 + A: they win.     -> 3 losses.
#            the other 44 - 5 - 3 = 36 (including 7s, 7h quad sevens and 2c, 2d for 222 77): both play the
#            same five cards (77 22 or better plus ace kicker): tie.
# eq = (5 + 36/2) / 44 = 23/44. adjusted = 23/44 * 40000 - 20000 = 20909.09 - 20000 = +909.09.
# (Tie counted as 0 would give -15454.5, tie counted as 1 would give +41/44*40000-20000 = 17272.7.)
H_SPLIT = hand("b200c/kk/b19800c/", 0, ["Ah", "Kd"], ["As", "Qc"], ["2s", "2h", "7d", "7c", "9c"])
SPLIT_EQ = 23 / 44
SPLIT_ADJ = SPLIT_EQ * 40000 - 20000

# Hands where adjusted = winnings.
H_FOLD = hand("b200f", -100, ["As", "Ah"], ["Kd", "Kc"], [])                       # we fold the big blind: -100
H_ALLIN_FOLD = hand("b20000f", -100, ["7s", "2h"], ["Kd", "Kc"], [], 0)            # all-in shove, we fold: -100
H_RIVER = hand("b200c/kk/kk/kk", 200, ["As", "Ah"], ["Kd", "Kc"],                  # river showdown, no all-in: +200
               ["2d", "7c", "9h", "4c", "3s"])
H_RIVER_ALLIN = hand("b200c/kk/kk/b19800c", -20000, ["As", "Ah"], ["Kd", "Kc"],    # all-in called ON the river: no
                     ["2d", "7c", "9h", "4c", "Kh"])                                # cards to come, so winnings
H_UNKNOWN = dict(H_FLOP, bot_hole=[])                                               # opponent cards unknown: winnings


def test_helper_brute_force_matches_hand_counts():
    # Guards the hand derivations above against my own slips; pokerkit is the judge, not the tool.
    assert math.isclose(brute_eq(["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h"]), FLOP_EQ, abs_tol=1e-12)
    assert math.isclose(brute_eq(["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h", "4c"]), TURN_EQ, abs_tol=1e-12)
    assert math.isclose(brute_eq(["Ah", "Kd"], ["As", "Qc"], ["2s", "2h", "7d", "7c"]), SPLIT_EQ, abs_tol=1e-12)


def test_preflop_aa_vs_kk():
    r = result([H_PRE])
    # raw -20000; adjusted about +12704 (Monte Carlo, +-400)
    assert r["hands"] == 1 and r["n_adjusted"] == 1
    assert r["raw_chips"] == -20000
    assert abs(r["adjusted_chips"] - PRE_ADJ) < 400, r["adjusted_chips"]


def test_flop_all_in_exact():
    r = result([H_FLOP])
    assert r["n_adjusted"] == 1 and r["raw_chips"] == -20000
    assert abs(r["adjusted_chips"] - 16646.46) < 0.01, r["adjusted_chips"]
    assert abs(r["adjusted_chips"] - FLOP_ADJ) < 0.01
    # cross-check: the same number from a pokerkit brute force over the 990 run-outs
    assert abs(r["adjusted_chips"] - (brute_eq(["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h"]) * 40000 - 20000)) < 0.01


def test_turn_all_in_exact():
    r = result([H_TURN])
    assert r["n_adjusted"] == 1
    assert abs(r["adjusted_chips"] - 18181.82) < 0.01, r["adjusted_chips"]
    assert abs(r["adjusted_chips"] - (brute_eq(["As", "Ah"], ["Kc", "Kd"], ["2d", "7c", "9h", "4c"]) * 40000 - 20000)) < 0.01


def test_split_counts_half():
    r = result([H_SPLIT])
    assert r["raw_chips"] == 0 and r["n_adjusted"] == 1
    assert abs(r["adjusted_chips"] - 909.09) < 0.01, r["adjusted_chips"]


def test_other_hands_adjusted_equals_winnings():
    hands = [H_FOLD, H_ALLIN_FOLD, H_RIVER, H_RIVER_ALLIN, H_UNKNOWN]
    r = result(hands)
    # winnings: -100 - 100 + 200 - 20000 - 20000 = -40000; none adjusted.
    assert r["hands"] == 5 and r["n_adjusted"] == 0
    assert r["raw_chips"] == -40000 and r["adjusted_chips"] == -40000
    assert r["adjusted_bb100"] == r["raw_bb100"] == -8000      # -40000 / 5 hands
    assert r["sd_adjusted"] == r["sd_raw"]


def test_headline_numbers_and_interval():
    # Four hands: H_TURN (adjusted +18181.82), H_FOLD (-100), H_RIVER (+200), H_SPLIT (+909.09).
    # raw: -20000, -100, +200, 0 -> sum -19900, mean -4975 -> bb/100 = -4975.
    # raw sample SD: deviations from -4975: -15025, 4875, 5175, 4975.
    #   squares: 225750625 + 23765625 + 26780625 + 24750625 = 301047500; /3 = 100349166.7; sd = 10017.45.
    # raw half-width = 1.96 * 10017.45 / sqrt(4) = 9817.1 -> [-14792.1, +4842.1].
    # adjusted: 18181.82 - 100 + 200 + 909.09 = 19190.91; mean 4797.73 -> bb/100 = +4797.73.
    #   deviations: 13384.09, -4897.73, -4597.73, -3888.64
    #   squares: 179,124,000 + 23,987,800 + 21,139,100 + 15,121,400 = 239,372,300 (approx); /3 = 79,790,800;
    #   sd = 8932.6; half-width = 1.96 * 8932.6 / 2 = 8754.0 -> [-3956.3, +13551.7]. (tolerance 5, rounding)
    r = result([H_TURN, H_FOLD, H_RIVER, H_SPLIT])
    assert r["hands"] == 4 and r["n_adjusted"] == 2
    assert r["raw_chips"] == -19900 and r["raw_bb100"] == -4975
    assert abs(r["sd_raw"] - 10017.45) < 1
    lo, hi = r["raw_ci95"]
    assert abs(lo - -14792.1) < 5 and abs(hi - 4842.1) < 5
    assert abs(r["adjusted_chips"] - 19190.91) < 0.05 and abs(r["adjusted_bb100"] - 4797.73) < 0.02
    assert abs(r["sd_adjusted"] - 8932.6) < 5
    assert abs(r["sd_ratio"] - 8932.6 / 10017.45) < 0.001       # sd_adjusted / sd_raw = 0.8917
    lo, hi = r["adjusted_ci95"]
    assert abs(lo - -3956.3) < 5 and abs(hi - 13551.7) < 5


def test_spread_drops():
    # 8 turn all-ins AA vs KK: 4 where they hit a K (-20000), 4 where we win (+20000).
    # raw mean 0, sample SD = 20000 * sqrt(8/7) = 21380.9. Every adjusted hand is the same 18181.82, so
    # adjusted SD = 0 and the ratio is 0.
    win = dict(H_TURN, winnings=20000, expected=20000, board=["2d", "7c", "9h", "4c", "3s"])
    r = result([H_TURN] * 4 + [win] * 4)
    assert r["hands"] == 8 and r["n_adjusted"] == 8 and r["raw_chips"] == 0
    assert abs(r["sd_raw"] - 21380.9) < 1
    assert r["sd_adjusted"] < 0.01 * r["sd_raw"] and r["sd_ratio"] < 0.01
    assert abs(r["adjusted_bb100"] - 18181.82) < 0.01
    lo, hi = r["adjusted_ci95"]
    assert lo <= r["adjusted_bb100"] <= hi and hi - lo < 1     # interval collapses with zero SD


def test_two_logs_concatenate_and_per_log_rows():
    a, b = [H_FLOP, H_FOLD], [H_TURN, H_RIVER]
    r = result(a, b)
    # log a: raw -20000 - 100 = -20100; adjusted 16646.46 - 100 = 16546.46 (1 adjusted)
    # log b: raw -20000 + 200 = -19800; adjusted 18181.82 + 200 = 18381.82 (1 adjusted)
    # together: 4 hands, raw -39900, adjusted 34928.28, 2 adjusted.
    assert r["hands"] == 4 and r["n_adjusted"] == 2 and r["raw_chips"] == -39900
    assert abs(r["adjusted_chips"] - 34928.28) < 0.05
    ra, rb = r["logs"]
    assert (ra["hands"], ra["raw_chips"], ra["n_adjusted"]) == (2, -20100, 1)
    assert abs(ra["adjusted_chips"] - 16546.46) < 0.02
    assert (rb["hands"], rb["raw_chips"], rb["n_adjusted"]) == (2, -19800, 1)
    assert abs(rb["adjusted_chips"] - 18381.82) < 0.02
    # the combined numbers equal one log holding all four hands
    one = result(a + b)
    for k in ("hands", "raw_chips", "adjusted_chips", "sd_raw", "sd_adjusted", "n_adjusted"):
        assert math.isclose(one[k], r[k], abs_tol=1e-9), k


def test_empty_log():
    rc, out, _ = run([])
    assert rc == 0 and "0 hands" in out, out
    rc, out, js = run([], out_json=True)
    assert rc == 0 and js["hands"] == 0


def test_two_runs_identical():
    # AA vs KK preflop uses the Monte Carlo path; a fixed seed makes stdout and JSON repeat exactly.
    logs = [[H_PRE, H_FLOP, H_FOLD]]
    rc1, out1, js1 = run(*logs, out_json=True)
    rc2, out2, js2 = run(*logs, out_json=True)
    assert rc1 == rc2 == 0
    assert out1 == out2 and js1 == js2


# --- P1b: per-street luck correction ------------------------------------------------------------------
# street_adjusted = winnings + sum over each board deal of P_at_deal * (eq_before - eq_after), where P is the
# total of both players' contributions after the betting of the previous street. Slumbot bet sizes are
# "raise to" street totals; each player puts in the same amount when a bet is called, so after
# "b200c/b300c/b600c" each side has put in 1100 and the pot at the river deal is 2200.
# The expected values below come from my own pokerkit brute force (brute_eq), not from the tool.
AA, KK = ["As", "Ah"], ["Kc", "Kd"]
FLOP3, TURN1 = ["2d", "7c", "9h"], "4c"
PRE_EQ = 0.8176                      # AA vs KK preflop, as in H_PRE above


def river_hand(river, t, win_sign=None):
    """AA vs KK, flop 2d 7c 9h, turn 4c, given river. Flop bet 300 called, turn bet t (0 = checked through),
    no river betting. Pot at the river deal = 400 + 600 + 2t = 1000 + 2t; each side has put in 500 + t."""
    turn_act = f"b{t}c" if t else "kk"
    a = KK + [river]
    ours = StandardHighHand.from_game("".join(AA), "".join(FLOP3) + TURN1 + river)
    theirs = StandardHighHand.from_game("".join(KK), "".join(FLOP3) + TURN1 + river)
    score = 1 if ours > theirs else 0.5 if ours == theirs else 0
    win = (2 * score - 1) * (500 + t)
    return hand(f"b200c/b300c/{turn_act}/kk", win, AA, KK, FLOP3 + [TURN1, river]), score


def unseen_rivers():
    return [c for c in DECK if c not in AA + KK + FLOP3 + [TURN1]]


def test_zero_mean_river_corrections_exact():
    rivers = unseen_rivers()
    assert len(rivers) == 44
    eq_turn = brute_eq(AA, KK, FLOP3 + [TURN1])

    def excess(t):          # sum over all 44 rivers of (street_adjusted - winnings); one log, one run
        hs = [river_hand(r, t)[0] for r in rivers]
        r = result(hs)
        assert r["n_street_adjusted"] == 44
        return r["street_chips"] - r["raw_chips"]

    # Flop and turn corrections are identical in all 44 hands and do not depend on the turn bet t (they use the
    # pot before it). Only the river term has P = 1000 + 2t, so S(t) = 44*K + P(t) * sum_r(eq_turn - score_r).
    # The sum is 0 exactly, so S(1000) - S(0) = 2000 * 0 and the river terms cancel to within 1e-6 * P.
    s0, s1 = excess(0), excess(1000)
    assert abs(s1 - s0) < 1e-6 * 3000, (s0, s1)
    # Non-vacuous: single rivers give exact, non-zero corrections 2t * (eq_turn - score) on top of the t=0 value.
    for river in ("Kh", "3s"):
        h0, sc = river_hand(river, 0)
        h1, _ = river_hand(river, 1000)
        r0, r1 = result([h0]), result([h1])
        d = (r1["street_chips"] - r1["raw_chips"]) - (r0["street_chips"] - r0["raw_chips"])
        assert abs(d - 2000 * (eq_turn - sc)) < 1e-6 * 3000, (river, d)
        assert abs(2000 * (eq_turn - sc)) > 1            # a real correction, not 0


def test_street_matches_p1_for_preflop_all_in():
    r = result([H_PRE])
    assert r["n_street_adjusted"] == 1 and r["raw_chips"] == -20000
    # pot is 40,000 at every deal, so the corrections telescope to 40000 * (eq_pre - actual score 0).
    assert abs(r["street_chips"] - PRE_ADJ) < 400, r["street_chips"]
    assert abs(r["street_chips"] - r["adjusted_chips"]) < 400
    assert abs(r["adjusted_chips"] - PRE_ADJ) < 400            # P1's figure is unchanged


def test_river_showdown_no_all_in_several_streets():
    # AA vs KK, board 2d 7c 9h 4c 3s, "b200c/b300c/b600c/b1000c": P = 400 (flop), 1000 (turn), 2200 (river).
    # We win 200+300+600+1000 = 2100 (AA holds on this board).
    h = hand("b200c/b300c/b600c/b1000c", 2100, AA, KK, FLOP3 + [TURN1, "3s"])
    e_flop = brute_eq(AA, KK, FLOP3)
    e_turn = brute_eq(AA, KK, FLOP3 + [TURN1])
    e_river = brute_eq(AA, KK, FLOP3 + [TURN1, "3s"])
    assert e_river == 1
    exact = 1000 * (e_flop - e_turn) + 2200 * (e_turn - e_river)
    flop_term = 400 * (PRE_EQ - e_flop)                        # preflop equity is Monte Carlo in the tool
    r = result([h])
    assert r["n_street_adjusted"] == 1 and r["raw_chips"] == 2100
    want = 2100 + exact + flop_term
    assert abs(r["street_chips"] - want) < 0.01 * 400 + 1e-6 * 2200, (r["street_chips"], want)
    assert r["adjusted_chips"] == 2100 and r["n_adjusted"] == 0      # P1 untouched: no all-in


def test_street_fold_preflop_is_winnings():
    r = result([H_FOLD, H_ALLIN_FOLD])
    assert r["raw_chips"] == -200 and r["street_chips"] == -200 and r["n_street_adjusted"] == 0
    assert r["sd_street"] == r["sd_raw"]


def test_street_unknown_bot_hole_is_winnings():
    h = hand("b200c/b300c/b600c/b1000c", 2100, AA, [], FLOP3 + [TURN1, "3s"])
    r = result([h, H_UNKNOWN])
    assert r["n_street_adjusted"] == 0
    assert r["street_chips"] == r["raw_chips"] == 2100 - 20000


def test_street_sd_below_raw():
    # 44 hands that differ only in the river card, river check-through: pot 1000 at the river deal, each hand
    # wins/loses/ties 500. winnings + 1000 * (eq_turn - score) = 1000 * eq_turn - 500, the same for all 44
    # (score = (winnings + 500) / 1000), so the street-adjusted spread is 0 while the raw spread is large.
    hs = [river_hand(c, 0)[0] for c in unseen_rivers()]
    r = result(hs)
    assert r["sd_raw"] > 300, r["sd_raw"]
    assert r["sd_street"] < 0.01 * r["sd_raw"], (r["sd_street"], r["sd_raw"])
    assert r["sd_ratio_street"] < 0.01
    assert math.isclose(r["sd_ratio_street"], r["sd_street"] / r["sd_raw"], abs_tol=1e-12)


STREET_KEYS = ("street_chips", "street_bb100", "street_ci95", "sd_street", "sd_ratio_street", "n_street_adjusted")


def test_street_fields_exist_total_and_per_log():
    r = result([H_PRE, H_FLOP, H_FOLD], [H_TURN, H_RIVER])
    rows = [r] + r["logs"]
    assert len(r["logs"]) == 2
    for row in rows:
        for k in STREET_KEYS:
            assert k in row, k
        lo, hi = row["street_ci95"]
        assert lo <= row["street_bb100"] <= hi
        assert math.isclose(row["street_bb100"], row["street_chips"] / row["hands"], rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(row["sd_ratio_street"], row["sd_street"] / row["sd_raw"], rel_tol=1e-9)
    assert r["n_street_adjusted"] == 4       # H_PRE, H_FLOP, H_TURN, H_RIVER have deals; H_FOLD none
    assert r["logs"][1]["n_street_adjusted"] == 2


def test_street_two_runs_identical():
    logs = [[H_PRE, H_FLOP, H_FOLD, river_hand("Kh", 0)[0]]]
    rc1, out1, js1 = run(*logs, out_json=True)
    rc2, out2, js2 = run(*logs, out_json=True)
    assert rc1 == rc2 == 0
    assert "street_chips" in js1 and "street_ci95" in js1["logs"][0]      # not vacuously equal
    assert out1 == out2 and js1 == js2


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
