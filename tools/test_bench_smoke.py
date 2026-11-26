"""Seeded bench smoke for the bot adapter: bench.py --hero bot (live wire) vs reference, 200 hands.
Run from the repo root: PYTHONPATH=chipzen python tools/test_bench_smoke.py

Checks the run exits 0, no decision is illegal against the legal set it was offered, and the
adapter never fell back. bench.py silently coerces an illegal answer and has no counter for it,
so legality is read from bot.py's own per-decision log line, switched on by the wrapper below."""
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


def illegal(log):
    """Decisions whose action is not in the legal set it was offered, or a raise outside the band."""
    bad, n = [], 0
    for line in log.splitlines():
        m = DECISION.search(line)
        if not m:
            continue
        n += 1
        lo, hi, legal, act, amt = m.groups()
        if act not in legal.split(","):
            bad.append(line)
        elif act == "raise" and not int(lo) <= int(amt) <= int(hi):
            bad.append(line)
    return n, bad


def check(rc, log, dump):
    assert rc == 0, "bench exit %s: %s" % (rc, log[-400:])
    n, bad = illegal(log)
    assert n > 0, "no decision lines seen: the legality check would pass vacuously"
    assert not bad, "%d illegal action(s), first: %s" % (len(bad), bad[0])
    assert "ENGINE FAILED" not in log, "adapter fell back to check/fold"
    assert len(json.load(open(dump))["results"]) == 100, "expected 100 duplicate pairs"
    return n


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "dump.json")
        rc, log = smoke(dump)
        print("OK: %d decisions, no illegal action, no fallback" % check(rc, log, dump))
