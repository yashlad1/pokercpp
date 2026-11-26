"""Black-box tests for the bench opponent `pushfold` (#76).
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_pushfold.py

Expected push frequencies come from the table itself (chipzen/pushfold.h at research/pushfold c3b06d9),
parsed here from `git show`, not by bench. Class order is bench's PREFLOP_PCT key order. Other uses are
bench's public surface: View, OPPONENTS, Reference.act and the command line."""
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bench  # noqa: E402

ENV = dict(os.environ, PYTHONPATH="chipzen")
BB = 100
CLASSES = list(bench.PREFLOP_PCT)  # (high rank 2..14, low rank, suited), in preflop_ranks.h order
RANKS = "23456789TJQKA"


def load_table():
    txt = subprocess.run(["git", "show", "c3b06d9:chipzen/pushfold.h"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    rows = {float(s): [int(x) for x in r.split(",")] for r, s in re.findall(r"\{([\d,]+)\},\s*//\s*([\d.]+) bb", txt)}
    assert len(rows) == 39 and all(len(r) == 169 for r in rows.values())
    return rows


TABLE = load_table()


def freq(eff_bb, cls_idx):
    """Table frequency: the largest row stack at or below eff_bb, the 1.0 row below that."""
    row = max([s for s in TABLE if s <= eff_bb + 1e-9] or [1.0])
    return TABLE[row][cls_idx]


def hole_of(cls):
    hi, lo, suited = cls
    if hi == lo:
        return [RANKS[hi - 2] + "h", RANKS[lo - 2] + "d"]
    return [RANKS[hi - 2] + "s", RANKS[lo - 2] + ("s" if suited else "d")]


def small_blind(hole, own_bb, other_bb=None, hand=1, **kw):
    """The small blind's first action: posted 50, big blind posted 100, stacks are totals at hand start."""
    own, other = int(own_bb * BB), int((own_bb if other_bb is None else other_bb) * BB)
    v = dict(hole=hole, board=[], pot=150, to_call=50, min_raise=200, max_raise=own, stack=own - 50, bb=BB,
             villain_raises=0, hand=hand, history=[], seat=0, dealer_seat=0, opp_stack=other - 100, live_history=None)
    v.update(kw)
    return bench.View(**v)


def act(name, v):
    return bench.OPPONENTS[name]().act(v)


def same_as_reference(v, what):
    got, want = act("pushfold", v), act("reference", v)
    assert got == want, "%s: got %r, Reference gives %r" % (what, got, want)


def check_deterministic(own_bb, other_bb=None):
    eff = min(own_bb, own_bb if other_bb is None else other_bb)
    n = 0
    for i, cls in enumerate(CLASSES):
        f = freq(eff, i)
        if f not in (0, 100):
            continue
        v = small_blind(hole_of(cls), own_bb, other_bb)
        want = ("raise", v.max_raise) if f == 100 else ("fold", 0)
        assert act("pushfold", v) == want, "%s at %s/%s bb (table %d): got %r, want %r" % (
            cls, own_bb, other_bb, f, act("pushfold", v), want)
        n += 1
    assert n > 40, "too few 0/100 classes tested at %s bb" % eff


def test_registered_and_in_all():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    out = subprocess.run([sys.executable, "tools/bench.py", "--vs", "nosuch"], cwd=ROOT, env=ENV,
                         capture_output=True, text=True).stderr
    assert "pushfold" in out, "pushfold is not among the --vs choices:\n%s" % out[-600:]


def test_pushes_and_folds_at_table_stacks():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    for s in (2, 3, 5, 8, 10, 13, 15, 20):
        check_deterministic(s)


def test_row_is_largest_stack_at_or_below():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    # the 7.0, 7.5 and 6.5 rows must differ somewhere, or this test could not tell them apart
    assert any(freq(7.0, i) in (0, 100) and freq(7.0, i) != freq(7.5, i) for i in range(169))
    check_deterministic(7.3)   # row 7.0, not 7.5
    check_deterministic(7.49)
    check_deterministic(4.99)  # row 4.5, not 5.0
    check_deterministic(0.9)   # under 1.0: the 1.0 row (every class pushes)
    check_deterministic(20.0)
    check_deterministic(19.9)  # row 19.5


def test_effective_stack_is_the_smaller_stack():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    check_deterministic(30, 7.3)  # short big blind decides
    check_deterministic(7.3, 30)  # short small blind decides
    check_deterministic(12, 12.4)


def test_mixed_frequency_share_and_determinism():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    N, TOL = 2000, 0.06  # sd of a share is at most sqrt(.25/2000) = 0.0112, so 0.06 is over 5 sd
    tested = 0
    for eff in (4.0, 6.0, 9.0, 12.0, 16.0):
        mixed = [i for i in range(169) if 10 <= freq(eff, i) <= 90]
        for i in mixed[:2]:
            f, hole = freq(eff, i), hole_of(CLASSES[i])
            ans = [act("pushfold", small_blind(hole, eff, hand=h)) for h in range(N)]
            assert all(a in (("raise", int(eff * BB)), ("fold", 0)) for a in ans), set(ans)
            share = sum(a[0] == "raise" for a in ans) / N
            assert abs(share - f / 100) <= TOL, "%s at %s bb: pushes %.3f, table %d%%" % (CLASSES[i], eff, share, f)
            again = [act("pushfold", small_blind(hole, eff, hand=h)) for h in range(N)]
            assert again == ans, "same hole and hand gave a different answer"
            tested += 1
    assert tested >= 5


def test_elsewhere_is_reference():
    assert "pushfold" in bench.OPPONENTS, "pushfold is not in OPPONENTS"
    holes = [hole_of(c) for c in CLASSES[::6]] + [["As", "Kd"], ["7s", "2d"], ["Jh", "Jd"]]
    for hole in holes:
        for eff in (20.5, 21, 40, 100):  # above 20 bb
            same_as_reference(small_blind(hole, eff), "%s at %s bb" % (hole, eff))
        # the big blind: acts after a limp (to_call 0), or facing a raise, short stacked
        same_as_reference(small_blind(hole, 10, pot=200, to_call=0, stack=900, opp_stack=900, max_raise=1000),
                          "big blind option %s" % hole)
        # facing a raise
        for eff in (5, 10, 20):
            same_as_reference(small_blind(hole, eff, pot=450, to_call=300, villain_raises=1, min_raise=600),
                              "facing a raise %s at %s bb" % (hole, eff))
            same_as_reference(small_blind(hole, eff, pot=1000, to_call=600, villain_raises=2, min_raise=1200),
                              "facing a re-raise %s at %s bb" % (hole, eff))
        # postflop, short stacked
        for board, pot in ((["Ac", "Kc", "9d"], 300), (["Ac", "Kc", "9d", "2h"], 500), (["Ac", "Kc", "9d", "2h", "3s"], 700)):
            for tc in (0, 100):
                same_as_reference(small_blind(hole, 10, board=board, pot=pot, to_call=tc, villain_raises=0),
                                  "postflop %s %s to_call %d" % (hole, board, tc))


def run_bench(vs):
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "d.json")
        r = subprocess.run([sys.executable, "tools/bench.py", "--hero", "bot", "--vs", vs, "--stack", "15",
                            "--hands", "200", "--seed0", "7", "--sims", "200", "--dump", dump], cwd=ROOT, env=ENV,
                           capture_output=True, text=True)
        assert r.returncode == 0, "bench --vs %s exit %s: %s" % (vs, r.returncode, (r.stdout + r.stderr)[-400:])
        return json.load(open(dump))["results"]


def test_results_differ_from_every_other_opponent():
    new = run_bench("pushfold")  # fails fast if not registered
    others = [n for n in bench.OPPONENTS if n != "pushfold"]
    with ThreadPoolExecutor(4) as ex:
        runs = dict(zip(others, ex.map(run_bench, others)))
    same = [m for m in runs if runs[m] == new]
    assert not same, "pushfold has the same results as %s" % same


if __name__ == "__main__":
    for t in (test_registered_and_in_all, test_pushes_and_folds_at_table_stacks, test_row_is_largest_stack_at_or_below,
              test_effective_stack_is_the_smaller_stack, test_mixed_frequency_share_and_determinism,
              test_elsewhere_is_reference, test_results_differ_from_every_other_opponent):
        t()
        print("ok", t.__name__)
    print("OK: pushfold bench opponent")
