"""Black-box test for B5 (paired McNemar compare) in tools/match.py.
Run from the repo root: PYTHONPATH=chipzen python tools/test_mcnemar.py"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MATCH = os.path.join(HERE, "match.py")
fails = []


def case(name, fn):
    try:
        fn()
        print("PASS %s" % name)
    except BaseException as e:
        fails.append(name)
        print("FAIL %s: %s: %s" % (name, type(e).__name__, e))


def run(*args):
    return subprocess.run([sys.executable, MATCH] + list(args), capture_output=True, text=True)


def write(path, rows):
    with open(path, "w") as f:
        for seed, won in rows:
            f.write(json.dumps({"opponent": "nit", "seed": seed, "won": won, "hands": [10, 10]}) + "\n")


def c1():
    import match
    m = match.mcnemar
    assert m(0, 0) == 1.0 and m(5, 5) == 1.0
    assert abs(m(10, 0) - 0.001953125) < 1e-12
    assert abs(m(7, 1) - 0.0703125) < 1e-12
    assert m(1, 7) == m(7, 1)


def pair_files(d, seed_b=None):
    a, b = os.path.join(d, "a.jsonl"), os.path.join(d, "b.jsonl")
    # 4 pairs = 8 matches; B flips 2 A-wins to losses and 1 A-loss to a win
    A = [(1, [True, True]), (2, [True, False]), (3, [False, False]), (4, [True, False])]
    B = [(1, [False, False]), (2, [True, True]), (3, [False, False]), (4, [True, False])]
    # discordant: seed1 two A-won/B-lost, seed2 one A-lost/B-won -> (2, 1)
    if seed_b:
        B[3] = (seed_b, B[3][1])
    write(a, A)
    write(b, B)
    return a, b


def c2():
    import match
    with tempfile.TemporaryDirectory() as d:
        r = run("--compare", *pair_files(d))
        assert r.returncode == 0, r.stderr
        line = [l for l in r.stdout.splitlines() if "discordant" in l]
        assert line, r.stdout
        # assumed: counts appear as "2" and "1"; p printed to >=3 decimals, so compare at 5e-4
        assert re.search(r"\b2\b", line[0]) and re.search(r"\b1\b", line[0]), line[0]
        p = float(re.search(r"p=\s*([0-9.]+(?:e-?\d+)?)", line[0]).group(1))
        assert abs(p - match.mcnemar(2, 1)) < 5e-4, (p, line[0])


def c3():
    with tempfile.TemporaryDirectory() as d:
        r = run("--compare", *pair_files(d, seed_b=99))
        assert r.returncode != 0
        assert "cannot pair" in r.stdout + r.stderr


def c4():
    with tempfile.TemporaryDirectory() as d:
        x, y = os.path.join(d, "x.jsonl"), os.path.join(d, "y.jsonl")
        for p in (x, y):
            r = run("--matches", "3", "--vs", "nit", "--hand-cap", "60", "--sims", "200",
                    "--seed0", "1", "--dump", p)
            assert r.returncode == 0, r.stderr[-300:]
            rows = [json.loads(l) for l in open(p) if l.strip()]
            assert len(rows) == 3, len(rows)
            for o in rows:
                assert isinstance(o["opponent"], str) and isinstance(o["seed"], int)
                assert len(o["won"]) == 2 and len(o["hands"]) == 2
        r = run("--compare", x, y)
        assert r.returncode == 0, r.stderr
        line = [l for l in r.stdout.splitlines() if "discordant" in l]
        assert line and len(re.findall(r"\b0\b", line[0])) >= 2, r.stdout


case("1 mcnemar values", c1)
case("2 compare 2/1", c2)
case("3 mismatched seeds", c3)
case("4 A/A run", c4)
sys.exit(1 if fails else 0)
