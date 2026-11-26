"""Seeded bench smoke for the bot adapter: bench.py --hero bot (live wire) vs reference, 200 hands.
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_smoke.py

Checks the run exits 0, bench coerced none of the hero's answers (meta.coerced == 0), and the
adapter never fell back. The wrapper below switches on bot.py's per-decision log line, so the
run is known to have made decisions."""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONPATH="chipzen")
# Same as running tools/bench.py, with the bot's INFO log on so each decision is visible.
WRAPPER = ("import logging, runpy, sys; logging.basicConfig(level=logging.INFO); "
           "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')")
DECISION = re.compile(r"min_raise=(\S+) max_raise=(\S+) .* legal=(\S+) .* -> (\w+)(?: (\d+))?$")


def smoke(dump):
    argv = [sys.executable, "-c", WRAPPER, "tools/bench.py", "--hero", "bot", "--vs", "reference",
            "--hands", "200", "--seed0", "20260", "--sims", "300", "--dump", dump]
    r = subprocess.run(argv, cwd=ROOT, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def decisions(log):
    return sum(1 for line in log.splitlines() if DECISION.search(line))


def check(rc, log, dump):
    assert rc == 0, "bench exit %s: %s" % (rc, log[-400:])
    n = decisions(log)
    assert n > 0, "no decision lines seen: the coerced check would pass vacuously"
    assert "ENGINE FAILED" not in log, "adapter fell back to check/fold"
    d = json.load(open(dump))
    assert len(d["results"]) == 100, "expected 100 duplicate pairs"
    assert d["meta"].get("coerced") == 0, "bench coerced %r hero answer(s)" % d["meta"].get("coerced")
    return n


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "dump.json")
        rc, log = smoke(dump)
        print("OK: %d decisions, nothing coerced, no fallback" % check(rc, log, dump))
