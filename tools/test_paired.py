"""Black-box tests for tools/paired.py (run: python tools/test_paired.py [path/to/tool])."""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "paired.py")


def base(results, **over):
    d = {"seed0": 1, "bb": 100, "stack_bb": 100, "opponent": "bot", "results": results}
    d.update(over)
    return d


def run(tmp, a, b):
    pa = os.path.join(tmp, "A.json")
    pb = os.path.join(tmp, "B.json")
    with open(pa, "w") as f:
        json.dump(a, f)
    with open(pb, "w") as f:
        json.dump(b, f)
    return subprocess.run([sys.executable, TOOL, pa, pb], capture_output=True, text=True)


def diff_line(out):
    for line in out.splitlines():
        if line.startswith("A - B:"):
            return line
    raise AssertionError("no 'A - B:' line in output:\n" + out)


def diff_value(out):
    m = re.search(r"A - B:\s*([+-]?\d+\.\d+)", out)
    assert m, "no signed number on A - B line:\n" + out
    return float(m.group(1))


def close_to(x, target, tol=0.05):
    return abs(x - target) <= tol


def test_identical_files(tmp):
    res = [100, -50, 200, 0, 30, 75]
    r = run(tmp, base(res), base(list(res)))
    assert r.returncode == 0, r.stdout + r.stderr
    line = diff_line(r.stdout)
    assert close_to(diff_value(r.stdout), 0.0), line
    assert "inconclusive" in line, line


def test_clearly_better(tmp):
    b_res = [(i * 13) % 200 for i in range(50)]
    a_res = [v + 500 + (10 if i % 2 == 0 else -10) for i, v in enumerate(b_res)]
    r = run(tmp, base(a_res), base(b_res))
    assert r.returncode == 0, r.stdout + r.stderr
    line = diff_line(r.stdout)
    assert close_to(diff_value(r.stdout), 250.0, 0.5), line
    assert "better" in line, line


def test_stack_mismatch(tmp):
    r = run(tmp, base([1, 2]), base([1, 2], stack_bb=200))
    assert r.returncode != 0, "expected nonzero exit"
    assert "cannot pair" in r.stdout + r.stderr, r.stdout + r.stderr


def test_length_mismatch(tmp):
    r = run(tmp, base([1, 2, 3, 4]), base([1, 2]))
    assert r.returncode != 0, "expected nonzero exit"
    assert "cannot pair" in r.stdout + r.stderr, r.stdout + r.stderr


def test_known_numbers(tmp):
    # A=[100,300], B=[0,0], bb=100, hands=4, hands/100=0.04.
    # A bb/100 = (400/100)/0.04 = 100.0. stdev(A)=141.42, n=2:
    # half-width = 1.96*141.42/sqrt(2)*2/100/0.04 = 98.0, so interval [2.0, 198.0].
    # Paired diffs are [100,300], so the A - B line is also 100.0 [2.0, 198.0].
    r = run(tmp, base([100, 300]), base([0, 0]))
    assert r.returncode == 0, r.stdout + r.stderr
    nums = [float(x) for x in re.findall(r"[+-]?\d+\.\d+", r.stdout)]
    for target in (100.0, 2.0, 198.0):
        assert any(close_to(x, target) for x in nums), (target, r.stdout)
    line = diff_line(r.stdout)
    line_nums = [float(x) for x in re.findall(r"[+-]?\d+\.\d+", line)]
    for target in (100.0, 2.0, 198.0):
        assert any(close_to(x, target) for x in line_nums), (target, line)


META = {"sims": 2000, "hero": "engine", "history": "full", "hand_number": "full",
        "impl": "cpu", "commit": "abc1234", "knobs": {}}


def with_meta(**over):
    m = dict(META)
    m.update(over)
    return base([100, -50, 200, 0], meta=m)


def check_meta_refused(tmp, key, value):
    r = run(tmp, with_meta(), with_meta(**{key: value}))
    out = r.stdout + r.stderr
    assert r.returncode != 0, "expected nonzero exit\n" + out
    assert "cannot pair" in out and "meta." + key in out, out


def test_meta_impl_mismatch(tmp):
    check_meta_refused(tmp, "impl", "metal")


def test_meta_sims_mismatch(tmp):
    check_meta_refused(tmp, "sims", 500)


def test_meta_hero_mismatch(tmp):
    check_meta_refused(tmp, "hero", "bot")


def test_meta_history_mismatch(tmp):
    check_meta_refused(tmp, "history", "noblinds")


def test_meta_hand_number_mismatch(tmp):
    check_meta_refused(tmp, "hand_number", "zero")


def test_meta_commit_knobs_may_differ(tmp):
    a = with_meta(commit="aaaa111", knobs={"x": 1})
    b = with_meta(commit="bbbb222", knobs={"x": 2})
    r = run(tmp, a, b)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "aaaa111" in r.stdout and "bbbb222" in r.stdout, r.stdout


def test_missing_meta_pairs_with_note(tmp):
    r = run(tmp, with_meta(), base([100, -50, 200, 0]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no metadata" in r.stdout + r.stderr, r.stdout + r.stderr


def test_bench_dump_has_meta(tmp):
    # Needs the engine built in chipzen/; runs from the repo root.
    root = os.path.dirname(HERE)
    out = os.path.join(tmp, "X.json")
    env = dict(os.environ, PYTHONPATH="chipzen")
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "bench.py"), "--vs", "reference", "--stack", "15",
         "--hands", "20", "--seed0", "1", "--dump", out],
        capture_output=True, text=True, cwd=root, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    with open(out) as f:
        meta = json.load(f).get("meta")
    assert meta is not None, "dump has no meta"
    assert meta.get("hero") == "engine", meta
    assert meta.get("sims") == 2000, meta
    assert meta.get("history") == "full", meta
    assert meta.get("hand_number") == "full", meta
    assert meta.get("impl") in ("cpu", "metal"), meta
    assert isinstance(meta.get("commit"), str) and meta["commit"], meta


def test_meta_wire_mismatch(tmp):
    r = run(tmp, with_meta(wire="bench"), with_meta(wire="live"))
    out = r.stdout + r.stderr
    assert r.returncode != 0, "expected nonzero exit\n" + out
    assert "cannot pair: meta.wire differs" in out, out


def test_meta_no_wire_pairs_with_bench(tmp):
    r = run(tmp, with_meta(), with_meta(wire="bench"))
    assert r.returncode == 0, r.stdout + r.stderr
    r = run(tmp, with_meta(wire="bench"), with_meta())
    assert r.returncode == 0, r.stdout + r.stderr


def test_meta_no_wire_vs_live_refused(tmp):
    for a, b in ((with_meta(), with_meta(wire="live")), (with_meta(wire="live"), with_meta())):
        r = run(tmp, a, b)
        out = r.stdout + r.stderr
        assert r.returncode != 0, "expected nonzero exit\n" + out
        assert "cannot pair" in out and "meta.wire" in out, out


def test_bench_dump_wire_default_bench(tmp):
    root = os.path.dirname(HERE)
    out = os.path.join(tmp, "X.json")
    env = dict(os.environ, PYTHONPATH="chipzen")
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "bench.py"), "--vs", "reference", "--stack", "15",
         "--hands", "20", "--seed0", "1", "--dump", out],
        capture_output=True, text=True, cwd=root, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    with open(out) as f:
        meta = json.load(f).get("meta")
    assert meta is not None and meta.get("wire") == "bench", meta


def main():
    import tempfile as tf

    tests = [
        test_identical_files,
        test_clearly_better,
        test_stack_mismatch,
        test_length_mismatch,
        test_known_numbers,
        test_meta_impl_mismatch,
        test_meta_sims_mismatch,
        test_meta_hero_mismatch,
        test_meta_history_mismatch,
        test_meta_hand_number_mismatch,
        test_meta_commit_knobs_may_differ,
        test_missing_meta_pairs_with_note,
        test_bench_dump_has_meta,
        test_meta_wire_mismatch,
        test_meta_no_wire_pairs_with_bench,
        test_meta_no_wire_vs_live_refused,
        test_bench_dump_wire_default_bench,
    ]
    failed = 0
    for t in tests:
        try:
            with tf.TemporaryDirectory() as tmp:
                t(tmp)
            print("PASS", t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", t.__name__, "-", str(e).strip()[:200])
    if failed:
        sys.exit(1)
    print("paired tests: all passed")


if __name__ == "__main__":
    main()
