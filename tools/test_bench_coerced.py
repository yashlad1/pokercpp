"""Black-box tests for the coerced-answer count in tools/bench.py (#146).
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_coerced.py

Each case runs the real bench command line, with the hero swapped for a stub that gives one
illegal answer whenever that answer can be illegal (and plays a legal check, call or fold otherwise). The stub is
planted by a small wrapper that runs bench.py's source with `PokerCpp` rebound to it, so
everything else, including the dump and the stdout lines, is bench itself. The stub also
reports how often it gave the illegal answer, so a case cannot pass without the situation arising."""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONPATH="chipzen")
WRAPPER = r'''
import atexit, os, sys
mode = os.environ["STUB_MODE"]
only_seat = os.environ.get("STUB_SEAT", "")
n = [0]
class Stub:
    name = "stub"
    def __init__(self, **kw): pass
    def act(self, v):
        # The legal baseline: check, call or fold, whichever is offered on every wire.
        ans = ("check", 0) if v.to_call == 0 else ("call", 0) if v.to_call < v.stack else ("fold", 0)
        base = ans
        if mode == "below_min" and v.max_raise > 0 and v.min_raise > 1:
            ans = ("raise", 1)
        elif mode == "above_max" and v.max_raise > 0:
            ans = ("raise", v.max_raise + 10 ** 6)
        elif mode == "raise_blocked" and v.max_raise <= 0:
            ans = ("raise", 100)
        elif mode == "fold_free" and v.to_call == 0:
            ans = ("fold", 0)
        if only_seat and str(v.seat) != only_seat:
            ans = base
        if ans != base:
            n[0] += 1
        return ans
atexit.register(lambda: print("stub_illegal", n[0]))
path = "tools/bench.py"
sys.argv = sys.argv[1:]
src = open(path).read().replace('if __name__ == "__main__":', "PokerCpp = Stub\nif __name__ == '__main__':", 1)
exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path, "Stub": Stub})
'''
# A "check or call when neither is possible" case is dropped: bench always offers check or call
# unless the hero is all-in (then it has no decision), so no state can reach it.
# No short-stack stub case: no bench opponent, stack from 2 to 100 bb, 200 hands, ever showed the
# hero min_raise > max_raise > 0, so that branch is covered by testing raise_amount_legal directly.
# case: (stub mode, opponent). The opponent is picked so the situation actually arises.
CASES = {
    "raise below the minimum": ("below_min", "station"),
    "raise above the maximum": ("above_max", "station"),
    "raise when no raise is possible": ("raise_blocked", "maniac"),
    # bench offers fold only facing a bet (it is not in the bot hero's valid_actions at to_call 0)
    "fold when fold is not offered": ("fold_free", "station"),
}


def bench(extra, mode=None, seat=""):
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "d.json")
        head = ["tools/bench.py"] if mode is None else ["-c", WRAPPER, "tools/bench.py"]
        argv = [sys.executable] + head + extra + ["--dump", dump]
        r = subprocess.run(argv, cwd=ROOT, env=dict(ENV, STUB_MODE=mode or "", STUB_SEAT=seat), capture_output=True, text=True)
        assert r.returncode == 0, "bench exit %s: %s" % (r.returncode, (r.stdout + r.stderr)[-500:])
        return r.stdout, json.load(open(dump))


def coerced_line(out):
    m = re.search(r"^coerced (\d+)$", out, re.M)
    assert m, "no 'coerced N' line on stdout:\n" + out
    return int(m.group(1))


def stub_run(mode, vs, seat=""):
    out, d = bench(["--hands", "40", "--vs", vs, "--seed0", "1"], mode, seat)
    given = int(re.search(r"^stub_illegal (\d+)$", out, re.M).group(1))
    return out, d, given


def test_each_case_is_counted():
    for name, (mode, vs) in CASES.items():
        out, d, given = stub_run(mode, vs)
        assert given > 0, "%s: the stub never got to give it, the case is vacuous" % name
        c = d["meta"].get("coerced")
        assert isinstance(c, int) and c > 0, "%s: meta.coerced is %r" % (name, c)
        assert coerced_line(out) == c, "%s: stdout and dump disagree" % name


def test_count_sums_both_seats():
    # Same illegal answer in only seat 0, only seat 1, and both: the run's count is the sum.
    c = [stub_run("above_max", "station", s)[1]["meta"].get("coerced") for s in ("0", "1", "")]
    assert all(isinstance(x, int) for x in c), c
    assert c[0] > 0 and c[1] > 0 and c[2] == c[0] + c[1], "seat 0, seat 1, both: %r" % c


def test_raise_amount_legal():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import bench
    f = bench.raise_amount_legal
    assert f(200, 200, 1000) and f(1000, 200, 1000) and f(500, 200, 1000)
    assert not f(199, 200, 1000) and not f(1001, 200, 1000)
    assert f(300, 500, 300) and not f(500, 500, 300) and not f(299, 500, 300)  # short stack: only max_raise


def test_match_compare_ignores_coerced():
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for n, c in (("A", 0), ("B", 3)):
            paths.append(os.path.join(tmp, n + ".jsonl"))
            with open(paths[-1], "w") as f:
                f.write(json.dumps({"meta": {"sims": 50, "hero": "engine", "coerced": c}}) + "\n")
                for s in range(4):
                    f.write(json.dumps({"opponent": "station", "seed": s, "won": [s % 2 == 0, True], "hands": [10, 10]}) + "\n")
        r = subprocess.run([sys.executable, "tools/match.py", "--compare"] + paths, cwd=ROOT, env=ENV,
                           capture_output=True, text=True)
    assert "cannot pair" not in r.stdout + r.stderr, r.stdout + r.stderr
    assert "discordant" in r.stdout, r.stdout + r.stderr


def test_legal_hero_counts_zero():
    out, d, given = stub_run("legal", "maniac")
    assert given == 0
    assert d["meta"].get("coerced") == 0, "meta.coerced is %r" % d["meta"].get("coerced")
    assert coerced_line(out) == 0


def test_engine_hero_reports_an_int():
    out, d = bench(["--hands", "4", "--sims", "50", "--vs", "reference", "--hero", "engine"])
    c = d["meta"].get("coerced")
    assert isinstance(c, int) and not isinstance(c, bool), "meta.coerced is %r" % c
    assert coerced_line(out) == c


def test_paired_ignores_coerced():
    _, d = bench(["--hands", "10", "--sims", "50", "--vs", "reference", "--hero", "engine"])
    e = json.loads(json.dumps(d))
    d["meta"]["coerced"], e["meta"]["coerced"] = 0, 7
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for n, x in (("A", d), ("B", e)):
            paths.append(os.path.join(tmp, n + ".json"))
            json.dump(x, open(paths[-1], "w"))
        r = subprocess.run([sys.executable, "tools/paired.py"] + paths, cwd=ROOT, capture_output=True, text=True)
    assert "cannot pair" not in r.stdout + r.stderr, r.stdout + r.stderr
    assert re.search(r"^A - B:", r.stdout, re.M), "no 'A - B:' line:\n" + r.stdout + r.stderr


if __name__ == "__main__":
    for t in (test_each_case_is_counted, test_count_sums_both_seats, test_raise_amount_legal,
              test_match_compare_ignores_coerced, test_legal_hero_counts_zero, test_engine_hero_reports_an_int,
              test_paired_ignores_coerced):
        t()
        print("ok", t.__name__)
    print("OK: bench counts coerced hero answers")
