"""Black-box checks for the call-narrowing option (#84): the engine's
villain_calls / call_narrow arguments and bot._villain_calls.

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_call_narrow.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from testutil import run
os.environ["POKERCPP_SIMS"] = "2000"

import pokercpp_engine
from chipzen import GameState
from chipzen.models import Card
import bot as botmod

SEED = 4242
LOG = os.path.join(HERE, "..", "results", "live-logs", "2026-11-24_222814-live.log")

PRE = dict(hole=["Qh", "Jd"], board=[], pot=300, to_call=200, min_raise=400, max_raise=9000, stack=9000, bb=100)
FLOP = dict(hole=["Qh", "Jd"], board=["Ks", "7c", "2d"], pot=400, to_call=200, min_raise=400, max_raise=9000, stack=9000, bb=100)
RIVER = dict(hole=["Ah", "Kd"], board=["Ks", "7c", "2d", "9h", "4s"], pot=1000, to_call=300, min_raise=600, max_raise=9000, stack=9000, bb=100)
FREE = dict(hole=["Ah", "Kd"], board=["Ks", "7c", "2d"], pot=400, to_call=0, min_raise=100, max_raise=9000, stack=9000, bb=100)


def decide(spot, **kw):
    return pokercpp_engine.decide(
        spot["hole"], spot["board"], spot["pot"], spot["to_call"], spot["min_raise"],
        spot["max_raise"], spot["stack"], spot["bb"], sims=500, seed=SEED, **kw)


def test_off_is_identical():
    for spot in (PRE, FLOP, RIVER, FREE):
        for vr in (0, 1, 2):
            for fl in (0.0, 0.5):
                base = decide(spot, villain_raises=vr, range_floor=fl)
                for k in (1, 2, 3):
                    got = decide(spot, villain_raises=vr, range_floor=fl, villain_calls=k)
                    assert got == base, (spot["board"], vr, fl, k, got, base)


def test_on_scales_by_factor_per_call():
    for spot in (PRE, FLOP, RIVER):
        for vr in (0, 1):
            r0 = decide(spot, villain_raises=vr, villain_calls=0, call_narrow=0.6)["range"]
            assert r0 == decide(spot, villain_raises=vr)["range"]
            for k in (1, 2):
                r = decide(spot, villain_raises=vr, villain_calls=k, call_narrow=0.6)["range"]
                assert abs(r - 0.6 ** k * r0) < 1e-12, (spot["board"], vr, k, r, r0)


def test_on_minimum_005():
    r0 = decide(FLOP, villain_raises=2)["range"]
    assert 0.6 ** 2 * r0 < 0.05 < 0.6 * r0, r0  # the spot really crosses the minimum
    assert decide(FLOP, villain_raises=2, villain_calls=2, call_narrow=0.6)["range"] == 0.05
    assert abs(decide(FLOP, villain_raises=2, villain_calls=1, call_narrow=0.6)["range"] - 0.6 * r0) < 1e-12


def test_on_range_floor_wins():
    r0 = decide(FLOP, villain_raises=0)["range"]
    assert 0.6 ** 2 * r0 < 0.5 < r0, r0
    for k in (1, 2):
        assert decide(FLOP, villain_raises=0, range_floor=0.5, villain_calls=k, call_narrow=0.6)["range"] == 0.5
    # a floor beats the 0.05 minimum too
    assert decide(FLOP, villain_raises=2, range_floor=0.1, villain_calls=2, call_narrow=0.6)["range"] == 0.1
    # a floor below the narrowed value changes nothing
    r = decide(FLOP, villain_raises=0, range_floor=0.1, villain_calls=1, call_narrow=0.6)["range"]
    assert abs(r - 0.6 * r0) < 1e-12, r


# ---- bot._villain_calls on hand-built histories ----

def C(s): return Card.from_str(s)


def H(seat, action, amount=0, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


def state(hist, your_seat=1):
    return GameState(hand_number=1, dealer_seat=0, your_seat=your_seat,
                     opponent_stacks=[1000], action_history=list(hist),
                     phase="preflop", hole_cards=[C("As"), C("Ad")], board=[],
                     pot=300, to_call=100, min_raise=200, max_raise=1000,
                     your_stack=1000, valid_actions=["fold", "call", "raise"])


BL = [H(0, "post_small_blind", 50), H(1, "post_big_blind", 100)]


def vc(hist, your_seat=1):
    return botmod._villain_calls(state(hist, your_seat))


def test_calls_small_blind_limp_is_zero():
    assert vc(BL + [H(0, "call", 50)]) == 0
    assert vc(BL + [H(0, "call", 50), H(1, "check")]) == 0


def test_calls_big_blind_calls_our_open():
    h = BL + [H(0, "raise", 300), H(1, "call", 200)]
    assert vc(h, your_seat=0) == 1


def test_calls_limp_then_call_of_a_raise():
    h = BL + [H(0, "call", 50), H(1, "raise", 300), H(0, "call", 200)]
    assert vc(h, your_seat=1) == 1


def test_calls_our_own_calls_never_count():
    h = BL + [H(0, "raise", 300), H(1, "call", 200)]
    assert vc(h, your_seat=1) == 0
    assert vc(h, your_seat=0) == 1


def test_calls_checks_and_blinds_never_count():
    h = BL + [H(0, "check", phase="flop"), H(1, "check", phase="flop"), H(0, "check", phase="turn")]
    assert vc(h) == 0 and vc(h, your_seat=0) == 0
    assert vc(BL) == 0 and vc(BL, your_seat=0) == 0


def test_calls_add_up_across_streets():
    h = BL + [H(0, "raise", 300), H(1, "call", 200),
              H(1, "check", phase="flop"), H(0, "bet", 200, "flop"), H(1, "call", 200, "flop"),
              H(1, "check", phase="turn"), H(0, "raise", 500, "turn"), H(1, "call", 500, "turn"),
              H(1, "check", phase="river")]
    assert vc(h, your_seat=0) == 3
    assert vc(h, your_seat=1) == 0


def test_calls_all_in_is_a_bet_not_a_call():
    h = BL + [H(0, "all_in", 1000), H(1, "call", 900)]
    assert vc(h, your_seat=0) == 1   # opponent calls our all-in
    assert vc(h, your_seat=1) == 0   # our call of their all-in
    h2 = BL + [H(0, "raise", 300), H(1, "all_in", 1000)]
    assert vc(h2, your_seat=0) == 0  # the opponent's all-in is aggression, not a call
    assert vc(h2, your_seat=1) == 0


def test_calls_perspective_follows_your_seat():
    h = BL + [H(0, "raise", 300), H(1, "call", 200),
              H(1, "bet", 200, "flop"), H(0, "call", 200, "flop")]
    assert vc(h, your_seat=0) == 1
    assert vc(h, your_seat=1) == 1
    h = h + [H(0, "bet", 300, "turn"), H(1, "call", 300, "turn")]
    assert vc(h, your_seat=0) == 2
    assert vc(h, your_seat=1) == 1


# ---- live wire: logged match 1 ----

LINE = re.compile(r"pokercpp INFO hand=(\d+) phase=(\w+) .* seat=(\d) .* hist=(\S+) hole=")


def logged_decisions():
    out = []
    for line in open(LOG):
        m = LINE.search(line)
        if m:
            hn, phase, seat, hist = m.groups()
            entries = [H(int(s), a, int(n)) for s, a, n in (e.split(":") for e in hist.split(","))]
            out.append((int(hn), phase, int(seat), entries))
    return out


def no_log(name):
    if os.path.exists(LOG):
        return False
    print("SKIP", name, "- results/live-logs not present (e.g. inside the Docker image)")
    return True


def test_live_every_logged_decision_counts():
    if no_log("test_live_every_logged_decision_counts"):
        return
    ds = logged_decisions()
    assert len(ds) > 150, len(ds)
    last = {}
    for hn, phase, seat, hist in ds:
        n = vc(hist, your_seat=seat)
        assert isinstance(n, int) and n >= 0, (hn, phase, n)
        assert n >= last.get(hn, 0), (hn, phase, n)  # the history only grows within a hand
        last[hn] = n


def test_live_hand_65_river_counts_the_callers():
    if no_log("test_live_hand_65_river_counts_the_callers"):
        return
    seen = {p: vc(h, your_seat=s) for hn, p, s, h in logged_decisions() if hn == 65}
    assert set(seen) == {"preflop", "flop", "turn", "river"}, seen
    assert seen["preflop"] == 0, seen
    assert seen["river"] >= 1, seen
    # opp called our preflop raise and our turn bet before the river decision
    assert seen == {"preflop": 0, "flop": 1, "turn": 1, "river": 2}, seen


if __name__ == "__main__":
    run(globals())
