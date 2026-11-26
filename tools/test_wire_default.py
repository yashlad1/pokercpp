"""Black-box test: --hero bot defaults to the live wire; --hero engine always records the bench wire.
Run from the repo root: PYTHONPATH=chipzen python tools/test_wire_default.py"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONPATH="chipzen")
TMP = tempfile.mkdtemp()
fails = []


def run(tool, hero, wire, tag):
    """Run a tool tiny; return (meta, results) from its dump."""
    dump = os.path.join(TMP, tag)
    common = ["--hero", hero, "--sims", "50", "--seed0", "7", "--vs", "nit", "--dump", dump]
    if tool == "bench":
        argv = ["tools/bench.py", "--hands", "4"] + common
    else:
        argv = ["tools/match.py", "--matches", "2", "--hand-cap", "6"] + common
    if wire:
        argv += ["--wire", wire]
    r = subprocess.run([sys.executable] + argv, cwd=ROOT, env=ENV, capture_output=True, text=True)
    assert r.returncode == 0, "%s exit %s: %s" % (argv, r.returncode, r.stderr[-300:])
    if tool == "bench":
        d = json.load(open(dump))
        return d["meta"], d["results"]
    recs = [json.loads(line) for line in open(dump)]
    return recs[0]["meta"], recs[1:]


def check(case, ok, got):
    if not ok:
        fails.append(case)
        print("FAIL %s got=%s" % (case, got))


for tool in ("bench", "match"):
    def go(case, fn):
        try:
            fn()
        except Exception as e:
            fails.append(case)
            print("FAIL %s %s: %s" % (case, type(e).__name__, e))

    def t_bot_default():
        m, res = run(tool, "bot", None, tool + "-bd")
        m2, res2 = run(tool, "bot", "live", tool + "-bl")
        check(tool + " bot default wire", m["wire"] == "live", m["wire"])
        check(tool + " bot default results == live", res == res2, (res, res2))

    def t_bot_bench():
        m, _ = run(tool, "bot", "bench", tool + "-bb")
        check(tool + " bot --wire bench", m["wire"] == "bench", m["wire"])

    def t_engine():
        m0, r0 = run(tool, "engine", None, tool + "-e0")
        m1, r1 = run(tool, "engine", "live", tool + "-e1")
        check(tool + " engine default wire", m0["wire"] == "bench", m0["wire"])
        check(tool + " engine --wire live meta", m1["wire"] == "bench", m1["wire"])
        check(tool + " engine results equal", r0 == r1, (r0, r1))

    go(tool + " bot default", t_bot_default)
    go(tool + " bot bench", t_bot_bench)
    go(tool + " engine", t_engine)

print("FAIL: %d case(s)" % len(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
