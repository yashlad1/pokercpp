"""Black-box tests for the coerced-answer count in tools/bench.py (#146).
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_coerced.py

Each case runs the real bench command line, with the hero swapped for a stub that gives one
illegal answer whenever that answer can be illegal (and plays call otherwise). The stub is
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
n = [0]
class Stub:
    name = "stub"
    def __init__(self, **kw): pass
    def act(self, v):
        ans = ("call", 0)
        if mode == "below_min" and v.max_raise > 0 and v.min_raise > 1:
            ans = ("raise", 1)
        elif mode == "above_max" and v.max_raise > 0:
            ans = ("raise", v.max_raise + 10 ** 6)
        elif mode == "raise_blocked" and v.max_raise <= 0:
            ans = ("raise", 100)
        elif mode == "fold_free" and v.to_call == 0:
            ans = ("fold", 0)
        if ans != ("call", 0):
            n[0] += 1
        return ans
atexit.register(lambda: print("stub_illegal", n[0]))
path = "tools/bench.py"
sys.argv = sys.argv[1:]
src = open(path).read().replace('if __name__ == "__main__":', "PokerCpp = Stub\nif __name__ == '__main__':", 1)
exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path, "Stub": Stub})
'''
# case: (stub mode, opponent). The opponent is picked so the situation actually arises.
CASES = {
    "raise below the minimum": ("below_min", "station"),
    "raise above the maximum": ("above_max", "station"),
    "raise when no raise is possible": ("raise_blocked", "maniac"),
    "fold with nothing to call": ("fold_free", "station"),
}


def bench(extra, mode=None):
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "d.json")
        head = ["tools/bench.py"] if mode is None else ["-c", WRAPPER, "tools/bench.py"]
        argv = [sys.executable] + head + extra + ["--dump", dump]
        r = subprocess.run(argv, cwd=ROOT, env=dict(ENV, STUB_MODE=mode or ""), capture_output=True, text=True)
        assert r.returncode == 0, "bench exit %s: %s" % (r.returncode, (r.stdout + r.stderr)[-500:])
        return r.stdout, json.load(open(dump))


def coerced_line(out):
    m = re.search(r"^coerced (\d+)$", out, re.M)
    assert m, "no 'coerced N' line on stdout:\n" + out
    return int(m.group(1))


def stub_run(mode, vs):
    out, d = bench(["--hands", "40", "--vs", vs, "--seed0", "1"], mode)
    given = int(re.search(r"^stub_illegal (\d+)$", out, re.M).group(1))
    return out, d, given


def test_each_case_is_counted():
    for name, (mode, vs) in CASES.items():
        out, d, given = stub_run(mode, vs)
        assert given > 0, "%s: the stub never got to give it, the case is vacuous" % name
        c = d["meta"].get("coerced")
        assert isinstance(c, int) and c > 0, "%s: meta.coerced is %r" % (name, c)
        assert coerced_line(out) == c, "%s: stdout and dump disagree" % name


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
    for t in (test_each_case_is_counted, test_legal_hero_counts_zero, test_engine_hero_reports_an_int,
              test_paired_ignores_coerced):
        t()
        print("ok", t.__name__)
    print("OK: bench counts coerced hero answers")
