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
    A = [(1, [True, True]), (2, [True, False]), (3, [False, False]), (4, [True, False])]
    B = [(1, [False, False]), (2, [True, True]), (3, [False, False]), (4, [True, False])]
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
            allr = [json.loads(l) for l in open(p) if l.strip()]
            meta = allr[0].get("meta")
            assert meta is not None, "no header"
            for k in ("sims", "hero", "hand_cap", "start_bb", "double_every", "impl", "commit"):
                assert k in meta, "meta missing " + k
            assert meta["hero"] == "engine", meta["hero"]
            rows = [o for o in allr if "meta" not in o]
            assert len(rows) == 3, len(rows)
            for o in rows:
                assert isinstance(o["opponent"], str) and isinstance(o["seed"], int)
                assert len(o["won"]) == 2 and len(o["hands"]) == 2
        r = run("--compare", x, y)
        assert r.returncode == 0, r.stderr
        line = [l for l in r.stdout.splitlines() if "discordant" in l]
        assert line and len(re.findall(r"\b0\b", line[0])) >= 2, r.stdout


def c5():
    base = {"sims": 200, "hero": "engine", "hand_cap": 60, "start_bb": 100,
            "double_every": None, "impl": "x", "commit": "aaa"}
    rows = [(1, [True, False]), (2, [False, False])]
    with tempfile.TemporaryDirectory() as d:
        def mk(name, **kw):
            p = os.path.join(d, name)
            write(p, rows)
            body = open(p).read()
            open(p, "w").write(json.dumps({"meta": dict(base, **kw)}) + "\n" + body)
            return p
        a, b, c = mk("a", ), mk("b", double_every=25), mk("c", commit="bbb")
        r = run("--compare", a, b)
        assert r.returncode != 0 and "meta.double_every" in r.stdout + r.stderr, r.stdout + r.stderr
        r = run("--compare", a, c)
        assert r.returncode == 0, r.stdout + r.stderr


def c6():
    base = {"sims": 200, "hero": "bot", "hand_cap": 60, "start_bb": 100,
            "double_every": None, "impl": "x", "commit": "aaa", "wire": "bench"}
    with tempfile.TemporaryDirectory() as d:
        ps = []
        for name, w in (("a", "bench"), ("b", "live")):
            p = os.path.join(d, name)
            write(p, [(1, [True, False])])
            body = open(p).read()
            open(p, "w").write(json.dumps({"meta": dict(base, wire=w)}) + "\n" + body)
            ps.append(p)
        r = run("--compare", *ps)
        assert r.returncode != 0 and "meta.wire" in r.stdout + r.stderr, r.stdout + r.stderr
        for name, extra, want in (("l", ["--wire", "live"], "live"), ("d", [], "live")):
            p = os.path.join(d, name)
            r = run("--matches", "2", "--vs", "nit", "--hand-cap", "60", "--sims", "200",
                    "--hero", "bot", *extra, "--seed0", "1", "--dump", p)
            assert r.returncode == 0, r.stderr[-300:]
            meta = json.loads(open(p).readline()).get("meta", {})
            assert meta.get("wire") == want, (want, meta)


def c7():
    import bot
    import match
    real = bot.PokerCppBot.decide

    def offered(wire):
        seen = []

        def spy(self, state):
            seen.append(list(state.valid_actions))
            return real(self, state)
        bot.PokerCppBot.decide = spy
        try:
            match.run("nit", 1, 60, 200, 1, hero="bot", wire=wire)
        finally:
            bot.PokerCppBot.decide = real
        return seen

    live, bench = offered("live"), offered("bench")
    assert live, "live: bot never asked to decide"
    assert not any("all_in" in v for v in live), "live wire offered all_in"
    assert any("all_in" in v for v in bench), "bench wire never offered all_in"


case("1 mcnemar values", c1)
case("2 compare 2/1", c2)
case("3 mismatched seeds", c3)
case("5 meta mismatch", c5)
case("6 wire", c6)
case("4 A/A run", c4)
case("7 wire reaches the bot", c7)
sys.exit(1 if fails else 0)
