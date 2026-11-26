"""Black-box checks for opponent.py (README "Memory floor").

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_opponent.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from testutil import run

from opponent import Opponent

PRIOR = 3


def close(a, b):
    return abs(a - b) < 1e-12


def feed(raises):
    o = Opponent()
    for i, r in enumerate(raises, start=1):
        o.saw(i, r)
    return o


def test_fresh_is_zero():
    o = Opponent()
    for k in (0, 1, 2, 3, 10):
        assert o.range_floor(k) == 0.0, (k, o.range_floor(k))


def test_k_below_one_is_zero():
    o = feed([3] * 20)
    assert o.range_floor(0) == 0.0, o.range_floor(0)
    assert o.range_floor(-1) == 0.0, o.range_floor(-1)


def test_same_hand_twice_keeps_max_not_sum():
    o = Opponent()
    o.saw(1, 1)
    o.saw(1, 1)
    assert o.range_floor(1) == 1 / (1 + PRIOR), o.range_floor(1)
    assert o.range_floor(2) == 0.0, "sum of 1+1 leaked: %r" % o.range_floor(2)
    o.saw(1, 3)
    o.saw(1, 2)  # a lower later count must not lower the max
    assert close(o.range_floor(3), 1 / (1 + PRIOR)), o.range_floor(3)
    assert close(o.range_floor(1), 1 / (1 + PRIOR)), "hand counted twice"


def test_one_hand():
    o = feed([2])
    assert close(o.range_floor(1), 1 / 4), o.range_floor(1)
    assert close(o.range_floor(2), 1 / 4), o.range_floor(2)
    assert o.range_floor(3) == 0.0, o.range_floor(3)


def test_five_hands():
    o = feed([1, 2, 3, 0, 1])  # 5 hands; >=1: 4, >=2: 2, >=3: 1
    for k, n in ((1, 4), (2, 2), (3, 1)):
        assert close(o.range_floor(k), n / 8), (k, o.range_floor(k), n / 8)


def test_twenty_hands_cycle():
    o = feed([i % 4 for i in range(1, 21)])  # 5 each of 0..3
    for k, n in ((1, 15), (2, 10), (3, 5)):
        assert close(o.range_floor(k), n / 23), (k, o.range_floor(k), n / 23)


def test_twenty_hands_all_three():
    o = feed([3] * 20)
    for k in (1, 2, 3):
        assert close(o.range_floor(k), 20 / 23), (k, o.range_floor(k))


def test_zero_raise_hands_still_count_as_seen():
    o = feed([0] * 20)
    for k in (1, 2, 3):
        assert o.range_floor(k) == 0.0, (k, o.range_floor(k))
    o.saw(21, 1)
    assert close(o.range_floor(1), 1 / 24), o.range_floor(1)


if __name__ == "__main__":
    run(globals())
