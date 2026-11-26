"""Black-box test (H-8, seeded half): the same build run twice at one seed pairs to exactly 0.0.
Drives tools/bench.py and tools/paired.py through their command lines only.
Run from the repo root: PYTHONPATH=chipzen python tools/test_aa_seeded.py"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONPATH="chipzen")
TMP = tempfile.mkdtemp()
NUM = r"([-+]?\d+(?:\.\d+)?)"
LINE = re.compile(r"^A - B:\s*" + NUM + r" bb/100\s+95% CI \[\s*" + NUM + r",\s*" + NUM + r"\]", re.M)


def run(argv):
    r = subprocess.run([sys.executable] + argv, cwd=ROOT, env=ENV, capture_output=True, text=True)
    assert r.returncode == 0, "%s exit %s: %s" % (argv, r.returncode, r.stderr[-300:])
    return r.stdout


def bench(hero, seed, tag):
    path = os.path.join(TMP, tag)
    run(["tools/bench.py", "--hero", hero, "--vs", "reference", "--hands", "100",
         "--seed0", str(seed), "--sims", "50", "--dump", path])
    return path


def paired_line(a, b):
    """Parse the one 'A - B:' line of paired.py into (diff, lo, hi)."""
    out = run(["tools/paired.py", a, b])
    lines = [x for x in out.splitlines() if x.startswith("A - B:")]
    assert len(lines) == 1, "want one 'A - B:' line, got %r" % lines
    m = LINE.match(lines[0])
    assert m, "unparsable: " + lines[0]
    return tuple(float(x) for x in m.groups())


def check_aa(a, b):
    assert json.load(open(a))["results"] == json.load(open(b))["results"], "results differ"
    got = paired_line(a, b)
    assert got == (0.0, 0.0, 0.0), "A/A not exactly zero: %r" % (got,)


if __name__ == "__main__":
    for hero in ("bot", "engine"):
        a, b = bench(hero, 11, hero + "A.json"), bench(hero, 11, hero + "B.json")
        assert len(json.load(open(a))["results"]) == 50, "want 50 pairs"
        print(hero, "paired line:", paired_line(a, b))
        check_aa(a, b)
    print("aa_seeded ok")
