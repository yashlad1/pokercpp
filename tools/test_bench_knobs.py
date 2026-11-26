"""Black-box tests for the bench opponent `knobs` (#77).
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_knobs.py

They use only bench's public surface: View, OPPONENTS, knobs_settings, PokerCpp's constructor and act,
and the command line. Each view is answered by a fresh opponent object, so engine memory carried
across calls is not tested."""
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
SETS = dict(realization_scale={0.8, 0.9, 1.0, 1.1, 1.2}, bluff_enabled={True, False},
            memory={True, False}, preflop_realization={0.65, 0.75, 0.85})


def view(**kw):
    return bench.View(**dict(BASE, **kw))


def test_registered_and_in_all():
    assert "knobs" in bench.OPPONENTS, "knobs is not in OPPONENTS"
    out = subprocess.run([sys.executable, "tools/bench.py", "--vs", "nosuch"], cwd=ROOT, env=ENV,
                         capture_output=True, text=True).stderr
    assert "knobs" in out, "knobs is not among the --vs choices (--vs all runs list(OPPONENTS)):\n%s" % out[-600:]


def test_settings_keys_values_and_coverage():
    seen = {k: set() for k in SETS}
    for seed in range(500):
        s = bench.knobs_settings(seed)
        assert set(s) == set(SETS), "keys %r" % sorted(s)
        assert s == bench.knobs_settings(seed), "seed %d is not deterministic" % seed
        for k, v in s.items():
            assert v in SETS[k], "%s=%r outside %r" % (k, v, SETS[k])
            seen[k].add(v)
    for k in SETS:
        assert seen[k] == SETS[k], "%s: over 500 seeds saw only %r" % (k, seen[k])


# preflop and postflop spots; hands cover several seeds, both seats of each pair
SPOTS = [dict(), dict(hole=["7h", "7d"], to_call=0, pot=200),
         dict(hole=["Qs", "Jd"], board=["Qh", "7c", "2d"], pot=600, to_call=300),
         dict(hole=["9h", "9d"], board=["Ah", "7c", "2d", "Ks"], pot=900, to_call=0),
         dict(hole=["Ac", "5c"], board=["Kc", "7c", "2d", "9s", "3h"], pot=1200, to_call=600)]


def test_play_equals_fresh_engine_from_settings():
    for i, spot in enumerate(SPOTS):
        for hand in (2 * i, 2 * i + 1, 40 + i, 41 + i, 1000 + 2 * i, 1001 + 2 * i):
            v = view(hand=hand, **spot)
            got = bench.OPPONENTS["knobs"]().act(v)
            want = bench.PokerCpp(sims=500, name="knobs", **bench.knobs_settings(hand // 2)).act(v)
            assert got == want, "hand %d %r: knobs %r, engine %r" % (hand, spot, got, want)


def test_both_seats_of_a_pair_share_settings():
    # settings come from hand // 2, so hands 2k and 2k+1 build the same engine
    for k in (0, 3, 17, 250):
        a = bench.knobs_settings(k)
        v0, v1 = view(hand=2 * k), view(hand=2 * k + 1)
        assert v0.hand // 2 == v1.hand // 2 == k
        want0 = bench.PokerCpp(sims=500, name="knobs", **a).act(v0)
        want1 = bench.PokerCpp(sims=500, name="knobs", **a).act(v1)
        assert bench.OPPONENTS["knobs"]().act(v0) == want0 and bench.OPPONENTS["knobs"]().act(v1) == want1


def run_bench(vs):
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "d.json")
        r = subprocess.run([sys.executable, "tools/bench.py", "--hero", "bot", "--vs", vs, "--hands", "200",
                            "--seed0", "7", "--sims", "200", "--dump", dump], cwd=ROOT, env=ENV,
                           capture_output=True, text=True)
        assert r.returncode == 0, "bench --vs %s exit %s: %s" % (vs, r.returncode, (r.stdout + r.stderr)[-400:])
        return json.load(open(dump))["results"]


def test_results_differ_from_every_other_opponent():
    mine = run_bench("knobs")  # fails fast if not registered
    others = [n for n in bench.OPPONENTS if n != "knobs"]
    with ThreadPoolExecutor(4) as ex:
        runs = dict(zip(others, ex.map(run_bench, others)))
    same = [m for m in runs if runs[m] == mine]
    assert not same, "knobs has the same results as %s" % same


if __name__ == "__main__":
    for t in (test_registered_and_in_all, test_settings_keys_values_and_coverage,
              test_play_equals_fresh_engine_from_settings, test_both_seats_of_a_pair_share_settings,
              test_results_differ_from_every_other_opponent):
        t()
        print("ok", t.__name__)
    print("OK: knobs bench opponent")
