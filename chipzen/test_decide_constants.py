"""Black-box pins for the README "How it decides" numbers, through the engine.

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_decide_constants.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from testutil import run

import pokercpp_engine

SEED = 4242
EPS = 1e-9


def decide(hole, board, pot, to_call, min_raise=100, max_raise=9000,
           stack=9000, bb=100, vr=0, **kw):
    return pokercpp_engine.decide(hole, board, pot, to_call, min_raise,
                                  max_raise, stack, bb, sims=2000,
                                  villain_raises=vr, seed=SEED, **kw)


def near(a, b, msg=""):
    assert abs(a - b) < EPS, "%s observed %r expected %r" % (msg, a, b)


FLOP = ["Ks", "7c", "2d"]
TURN = FLOP + ["9h"]
RIVER = TURN + ["3s"]
ROYAL = ["Qh", "Jh", "Th", "2c", "3d"]  # with Ah Kh: royal flush, the nuts


def test_range_by_raises_unfaced():
    for vr, want in ((0, 1.00), (1, 0.45), (2, 0.18), (3, 0.08), (7, 0.08)):
        d = decide(["Qh", "Jd"], FLOP, 200, 0, vr=vr)
        near(d["range"], want, "villain_raises=%d" % vr)


def test_small_bet_widens_by_1_3():
    # to_call 60 into pot 300 (pot-before 240): 25% < 35%
    for vr, want in ((1, 0.45 * 1.3), (2, 0.18 * 1.3), (3, 0.08 * 1.3), (0, 1.0)):
        d = decide(["Qh", "Jd"], FLOP, 300, 60, vr=vr)
        near(d["range"], want, "small bet vr=%d" % vr)


def test_big_bet_narrows_by_0_7():
    # to_call 150 into pot 300 (pot-before 150): 100% > 75%
    for vr, want in ((0, 0.7), (1, 0.45 * 0.7), (2, 0.18 * 0.7), (3, 0.08 * 0.7)):
        d = decide(["Qh", "Jd"], FLOP, 300, 150, vr=vr)
        near(d["range"], want, "big bet vr=%d" % vr)


def test_mid_bet_no_multiplier():
    # to_call 100 into pot 300 (pot-before 200): 50%
    d = decide(["Qh", "Jd"], FLOP, 300, 100, vr=1)
    near(d["range"], 0.45, "mid bet")


def test_thresholds_are_strict():
    # exactly 35% and exactly 75% of the pot before the bet: no multiplier
    d = decide(["Qh", "Jd"], FLOP, 270, 70, vr=1)  # 70/200
    near(d["range"], 0.45, "exactly 35%")
    d = decide(["Qh", "Jd"], FLOP, 350, 150, vr=1)  # 150/200
    near(d["range"], 0.45, "exactly 75%")


def test_range_clamped_to_unit_interval():
    d = decide(["Qh", "Jd"], FLOP, 300, 60, vr=0)
    assert d["range"] <= 1.0 + EPS, d["range"]
    for vr in (0, 1, 2, 3):
        d = decide(["Qh", "Jd"], FLOP, 300, 150, vr=vr)
        assert 0.05 - EPS <= d["range"] <= 1.0 + EPS, d["range"]


def test_realization_turn_and_river():
    d = decide(["Qh", "Jd"], TURN, 300, 100, vr=1)
    near(d["realized"] / d["equity"], 0.90, "turn")
    d = decide(["Qh", "Jd"], RIVER, 300, 100, vr=1)
    near(d["realized"] / d["equity"], 1.0, "river")


def test_checked_to_nuts_bets_66_percent():
    d = decide(["Ah", "Kh"], ROYAL, 1000, 0)
    assert d["action"] == "raise" and d["amount"] == int(1000 * 0.66), d
    d = decide(["Ah", "Kh"], ROYAL, 1234, 0)
    assert d["action"] == "raise" and d["amount"] == int(1234 * 0.66), d


def test_bet_clamped_to_band():
    d = decide(["Ah", "Kh"], ROYAL, 1000, 0, min_raise=800)
    assert d["action"] == "raise" and d["amount"] == 800, d
    d = decide(["Ah", "Kh"], ROYAL, 1000, 0, max_raise=500)
    assert d["action"] == "raise" and d["amount"] == 500, d


def test_facing_bet_strong_hand_raises_to_formula():
    pot, tc = 1000, 200
    want = int(0.75 * (pot + tc) + tc)  # 1100
    d = decide(["Ah", "Kh"], ROYAL, pot, tc)
    assert d["action"] == "raise" and d["amount"] == want, (d, want)
    # clamped
    d = decide(["Ah", "Kh"], ROYAL, pot, tc, max_raise=900)
    assert d["action"] == "raise" and d["amount"] == 900, d
    d = decide(["Ah", "Kh"], ROYAL, pot, tc, min_raise=1500)
    assert d["action"] == "raise" and d["amount"] == 1500, d


def test_short_stack_strong_hand_shoves():
    # 8 bb, AA preflop facing 100
    d = decide(["As", "Ad"], [], 300, 100, min_raise=200, max_raise=800,
               stack=800, bb=100, vr=1)
    assert d["action"] == "raise" and d["amount"] == 800, d


def test_short_stack_weak_hand_does_not_shove():
    d = decide(["7h", "2c"], [], 300, 100, min_raise=200, max_raise=800,
               stack=800, bb=100, vr=1)
    assert not (d["action"] == "raise" and d["amount"] == 800), d


def _boundary(stack):
    # 2h Qs on K-7-2: raw equity 0.59, checked to, so only the shove rule can fire
    return decide(["2h", "Qs"], FLOP, 200, 0, min_raise=100, max_raise=stack,
                  stack=stack, bb=100)


def test_short_stack_boundary_shoves_at_exactly_10bb():
    d = _boundary(1000)
    assert 0.55 <= d["equity"] < 0.62, d
    assert d["action"] == "raise" and d["amount"] == 1000, d


def test_short_stack_boundary_no_shove_at_10_5bb():
    d = _boundary(1050)
    assert not (d["action"] == "raise" and d["amount"] == 1050), d


if __name__ == "__main__":
    run(globals())
