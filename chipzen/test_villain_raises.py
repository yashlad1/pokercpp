"""Black-box checks for bot._villain_raises (README: opponent raise counting).

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_villain_raises.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from testutil import run
os.environ["POKERCPP_SIMS"] = "2000"

from chipzen import GameState
from chipzen.models import Card
import bot as botmod


def C(s): return Card.from_str(s)


def H(seat, action, amount=0):
    return {"seat": seat, "action": action, "amount": amount,
            "phase": "preflop", "is_timeout": False}


def state(valid, hist=(), your_seat=1):
    return GameState(hand_number=1, dealer_seat=0, your_seat=your_seat,
                     opponent_stacks=[1000], action_history=list(hist),
                     phase="preflop", hole_cards=[C("As"), C("Ad")], board=[],
                     pot=300, to_call=100, min_raise=200, max_raise=1000,
                     your_stack=1000, valid_actions=list(valid))


BL = [H(0, "post_small_blind", 50), H(1, "post_big_blind", 100)]


def vr(hist, your_seat=1):
    return botmod._villain_raises(state(["fold", "call"], hist=hist, your_seat=your_seat))


def test_villain_counts_each_aggressive_word():
    for word in ("raise", "bet", "all_in"):
        assert vr(BL + [H(0, word, 300)]) == 1, word


def test_villain_ignores_passive_words():
    for word in ("call", "check", "fold"):
        assert vr(BL + [H(0, word, 100)]) == 0, word


def test_villain_ignores_blind_posts():
    assert vr(BL) == 0
    assert vr([H(0, "post_big_blind", 100), H(1, "post_small_blind", 50)]) == 0


def test_villain_ignores_our_own_raises():
    h = BL + [H(1, "raise", 300), H(1, "bet", 300), H(1, "all_in", 900)]
    assert vr(h) == 0
    assert vr(h, your_seat=0) == 3


def test_villain_mixed_history():
    h = BL + [H(0, "raise", 300), H(1, "raise", 900), H(0, "call", 600),
              H(0, "bet", 200), H(0, "check"), H(0, "all_in", 5000), H(0, "fold")]
    assert vr(h) == 3, vr(h)


if __name__ == "__main__":
    run(globals())
