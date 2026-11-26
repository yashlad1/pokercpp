"""Black-box tests for the bench opponents `threebet` (#74) and `sizer` (#75).
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_opponents.py

They use only bench's public surface: View, OPPONENTS, the Reference opponent's act (as the
answer to "what would Reference do here") and the command line. Raise amounts are raise-to totals."""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bench  # noqa: E402

ENV = dict(os.environ, PYTHONPATH="chipzen")
BASE = dict(hole=["As", "Kd"], board=[], pot=400, to_call=200, min_raise=500, max_raise=9900, stack=9900,
            bb=100, villain_raises=1, hand=1, history=[], seat=0, dealer_seat=0, opp_stack=9700,
            live_history=None)


def view(**kw):
    return bench.View(**dict(BASE, **kw))


def act(name, **kw):
    return bench.OPPONENTS[name]().act(view(**kw))


def same_as_reference(name, **kw):
    got, want = act(name, **kw), act("reference", **kw)
    assert got == want, "%s %r: got %r, Reference gives %r" % (name, kw, got, want)


def near(got, want, what):
    assert got[0] == "raise" and abs(got[1] - want) <= 1, "%s: got %r, want raise to about %d" % (what, got, want)


# Facing our raise to 300 from the big blind: the opponent posted 100, so pot 400 and to_call 200.
# Raise-to is (pot + to_call) / 2 = 300, and 3x is 900. The same raise to 300 against a small blind of 50:
# pot 350, to_call 250.
FACING_RAISE = [dict(pot=400, to_call=200), dict(pot=350, to_call=250)]
THREEBET_RANGE = {"pair": ["7h", "7d"], "ace": ["Ah", "4d"], "broadways": ["Kh", "Jd"],
                  "9s": ["9h", "Td"], "suited connector": ["5h", "4h"]}


def test_both_are_registered_and_in_all():
    for n in ("threebet", "sizer"):
        assert n in bench.OPPONENTS, "%s is not in OPPONENTS" % n
    out = subprocess.run([sys.executable, "tools/bench.py", "--vs", "nosuch"], cwd=ROOT, env=ENV,
                         capture_output=True, text=True).stderr
    for n in ("threebet", "sizer"):
        assert n in out, "%s is not among the --vs choices (--vs all runs list(OPPONENTS)):\n%s" % (n, out[-600:])


def test_threebet_reraises_to_triple_in_range():
    for label, hole in THREEBET_RANGE.items():
        for spot in FACING_RAISE:
            near(act("threebet", hole=hole, **spot), 900, "%s %r" % (label, spot))


def test_threebet_reraise_is_clamped():
    near(act("threebet", hole=["7h", "7d"], min_raise=1000), 1000, "below min_raise")
    near(act("threebet", hole=["7h", "7d"], max_raise=800), 800, "above max_raise")


def test_threebet_outside_range_is_reference():
    for hole in (["7s", "2d"], ["8h", "3d"], ["Jh", "5d"], ["Th", "6c"]):
        for spot in FACING_RAISE:
            same_as_reference("threebet", hole=hole, **spot)


def test_threebet_facing_a_reraise():
    kw = dict(pot=1000, to_call=600, min_raise=1200, max_raise=9000, villain_raises=2)
    for hole in (["Th", "Td"], ["Jh", "Jd"], ["Ah", "Ad"], ["As", "Kd"], ["As", "Ks"]):
        assert act("threebet", hole=hole, **kw)[0] == "call", "should call with %r" % hole
    for hole in (["9h", "9d"], ["As", "Qd"], ["Ks", "Qs"], ["5h", "4h"], ["7s", "2d"]):
        assert act("threebet", hole=hole, **kw)[0] == "fold", "should fold with %r" % hole


def test_threebet_elsewhere_is_reference():
    for hole in (["As", "Kd"], ["7h", "7d"], ["5h", "4h"], ["7s", "2d"]):
        # postflop, facing a bet from us
        same_as_reference("threebet", hole=hole, board=["Ac", "Kc", "9d"], pot=300, to_call=150)
        # preflop, not facing a raise of ours
        same_as_reference("threebet", hole=hole, pot=150, to_call=50, min_raise=200, villain_raises=0)
        same_as_reference("threebet", hole=hole, pot=200, to_call=0, min_raise=100, villain_raises=0)
        # raising impossible
        same_as_reference("threebet", hole=hole, max_raise=0)


POST = dict(board=["Ac", "Kc", "9d"], pot=300, to_call=0, min_raise=100, villain_raises=0)


def test_sizer_value_bets_a_third_pot():
    for hole in (["As", "Kd"], ["Ah", "Ad"], ["9h", "9s"]):  # two pair, a flush-less set, trips-class hands
        near(act("sizer", hole=hole, **POST), 100, "value %r" % hole)
    near(act("sizer", hole=["As", "Kd"], **dict(POST, pot=900)), 300, "value, bigger pot")


def test_sizer_bluffs_one_and_a_half_pot():
    near(act("sizer", hole=["7s", "2d"], **POST), 450, "no pair")
    near(act("sizer", hole=["8h", "3d"], **dict(POST, pot=600)), 900, "no pair, bigger pot")


def test_sizer_checks_one_pair():
    for hole in (["As", "2d"], ["Kh", "3d"], ["9h", "4d"]):
        assert act("sizer", hole=hole, **POST) == ("check", 0), hole


def test_sizer_bets_are_clamped():
    near(act("sizer", hole=["As", "Kd"], **dict(POST, min_raise=200)), 200, "value, below min_raise")
    near(act("sizer", hole=["As", "Kd"], **dict(POST, max_raise=60)), 60, "value, above max_raise")
    near(act("sizer", hole=["7s", "2d"], **dict(POST, min_raise=500)), 500, "bluff, below min_raise")
    near(act("sizer", hole=["7s", "2d"], **dict(POST, max_raise=400)), 400, "bluff, above max_raise")


def test_sizer_elsewhere_is_reference():
    for hole in (["As", "Kd"], ["As", "2d"], ["7s", "2d"]):
        same_as_reference("sizer", hole=hole, **dict(POST, to_call=150, villain_raises=1))  # facing a bet
        same_as_reference("sizer", hole=hole, **dict(POST, max_raise=0))  # cannot bet
        for pre in (dict(pot=150, to_call=50, min_raise=200, villain_raises=0), dict(), dict(max_raise=0)):
            same_as_reference("sizer", hole=hole, **pre)  # preflop


def run_bench(vs):
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "d.json")
        r = subprocess.run([sys.executable, "tools/bench.py", "--hero", "bot", "--vs", vs, "--hands", "200",
                            "--seed0", "7", "--sims", "200", "--dump", dump], cwd=ROOT, env=ENV,
                           capture_output=True, text=True)
        assert r.returncode == 0, "bench --vs %s exit %s: %s" % (vs, r.returncode, (r.stdout + r.stderr)[-400:])
        return json.load(open(dump))["results"]


def test_results_differ_from_every_other_opponent():
    new = {n: run_bench(n) for n in ("threebet", "sizer")}  # fails fast if a name is not registered
    others = [n for n in bench.OPPONENTS if n not in new]
    with ThreadPoolExecutor(4) as ex:
        runs = dict(zip(others, ex.map(run_bench, others)))
    runs.update(new)
    for n in new:
        same = [m for m in runs if m != n and runs[m] == runs[n]]
        assert not same, "%s has the same results as %s" % (n, same)


if __name__ == "__main__":
    for t in (test_both_are_registered_and_in_all, test_threebet_reraises_to_triple_in_range,
              test_threebet_reraise_is_clamped, test_threebet_outside_range_is_reference,
              test_threebet_facing_a_reraise, test_threebet_elsewhere_is_reference,
              test_sizer_value_bets_a_third_pot, test_sizer_bluffs_one_and_a_half_pot,
              test_sizer_checks_one_pair, test_sizer_bets_are_clamped, test_sizer_elsewhere_is_reference,
              test_results_differ_from_every_other_opponent):
        t()
        print("ok", t.__name__)
    print("OK: threebet and sizer bench opponents")
