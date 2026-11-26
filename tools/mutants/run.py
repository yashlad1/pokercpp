#!/usr/bin/env python3
"""Mutation runner. Local only, never in CI.

Each mutant is applied in a throwaway detached worktree of HEAD (outside the
repo), rebuilt, and run against a named test set. A test kills a mutant when
it exits nonzero (a timeout counts as killed). Results are compared with the
catalogue's `expect` lists. The real working tree is never touched.

Catalogue: JSON list of {id, file, find, replace, what, expect, why_survives}.
`find` must match exactly once, otherwise the mutant is STALE (a failure).
`expect: []` marks a known survivor.

  PY=/path/to/python tools/mutants/run.py [--catalogue P] [--only A,B]
                                          [--tests T,U] [--out DIR]
Exit 1 if an expected test did not kill, a known survivor was killed, or a
mutant is STALE. Exit 2 if the repo state changed during the run.

Known limits (not fixed):
- A compile error in a `make` test counts as a kill (only the exit code is read).
- A timeout kills only the direct child, not its descendants.
- The before/after check is fatal only if a tracked file changed or one of
  this run's own worktrees is left over. Untracked files and other worktrees
  appearing or vanishing mid-run (other processes) are printed as notes.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

ROOT = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
PY = os.environ.get("PY") or sys.exit("set PY to the python with pybind11, pokerkit, chipzen-bot")
SOLVER_SRC = ["chipzen/solver.cpp", "montecarlo/MonteCarloSimulator.cpp",
              "model/advanced_hand_evaluator.cpp", "model/card.cpp", "model/deck.cpp"]

# name -> (argv with {py} and {solver}, extra env, timeout seconds). Mirrors .github/workflows/ci.yml.
# Anything not in the build-free group below needs the engine built first.
TESTS = {
    "solver": (["{py}", "chipzen/test_solver.py", "{solver}"], {}, 600),
    "sdk": (["{py}", "chipzen/test_bot_sdk.py"], {"PYTHONPATH": "chipzen"}, 600),
    "v4": (["{py}", "chipzen/test_v4.py"], {"PYTHONPATH": "chipzen", "POKERCPP_SIMS": "2000"}, 900),
    "logging": (["{py}", "chipzen/test_logging.py"], {}, 300),
    "engine_seed": (["{py}", "-m", "pytest"], {"PYTEST_ADDOPTS": "chipzen/test_engine_seed.py"}, 600),
    "replay": (["{py}", "chipzen/test_replay.py"], {"PYTHONPATH": "chipzen"}, 600),
    "preflop_realization": (["{py}", "chipzen/test_preflop_realization.py"], {}, 600),
    "paired": (["{py}", "tools/test_paired.py"], {}, 600),
    "opponent": (["{py}", "chipzen/test_opponent.py"], {"PYTHONPATH": "chipzen"}, 600),
    "decide_constants": (["{py}", "chipzen/test_decide_constants.py"], {"PYTHONPATH": "chipzen"}, 600),
    "villain_raises": (["{py}", "chipzen/test_villain_raises.py"], {"PYTHONPATH": "chipzen"}, 600),
    "wire": (["{py}", "chipzen/test_wire.py"], {"PYTHONPATH": "chipzen"}, 600),
    "parity": (["{py}", "tools/test_parity.py", "--pairs", "50"], {"PYTHONPATH": "chipzen"}, 1200),
    "match": (["{py}", "tools/test_match.py"], {"PYTHONPATH": "chipzen"}, 600),
    "decide_properties": (["make", "test_decide_properties"], {}, 900),
    "eval_exhaustive": (["make", "test_eval_exhaustive"], {}, 900),
}
MAKE_TESTS = {"decide_properties", "eval_exhaustive"}  # build and run themselves, no engine needed


def sh(argv, cwd, env=None, timeout=None):
    """Run, return (exit code or 'timeout', output tail)."""
    e = dict(os.environ, **(env or {}))
    try:
        p = subprocess.run(argv, cwd=cwd, env=e, text=True, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-600:]
    except subprocess.TimeoutExpired:
        return "timeout", ""


BASE = "HEAD"  # resolved to a SHA in main()


def snapshot():
    return [subprocess.check_output(c, cwd=ROOT, text=True)
            for c in (["git", "status", "--short"], ["git", "worktree", "list"])]


def run_mutant(m, tests, tmp):
    """Returns (status, {test: 'killed'|'survived'|'timeout'}, note). status: ok|STALE|BUILD-FAIL."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", m["id"]):
        return "BAD-ID", {}, "id must match [A-Za-z0-9_-]+"
    wt = os.path.join(tmp, "wt-" + m["id"])
    try:
        subprocess.run(["git", "worktree", "add", "--detach", wt, BASE], cwd=ROOT, check=True, capture_output=True)
        path = os.path.realpath(os.path.join(wt, m["file"]))
        if not path.startswith(os.path.realpath(wt) + os.sep):
            return "BAD-PATH", {}, f"{m['file']} escapes the worktree"
        src = open(path).read() if os.path.exists(path) else ""
        n = src.count(m["find"]) if m["find"] else 0
        if n != 1:
            return "STALE", {}, f"find matched {n} times in {m['file']}"
        open(path, "w").write(src.replace(m["find"], m["replace"]))
        need_engine = any(t not in MAKE_TESTS for t in tests)
        cpp = m["file"].split("/")[0] in ("chipzen", "montecarlo", "model") and not m["file"].endswith(".py")
        solver = os.path.join(tmp, "solver-" + m["id"])
        steps = []
        if need_engine:
            steps.append((["tools/build_engine.sh"], {"PY": PY}))
        if "solver" in tests:
            steps.append((["g++", "-std=c++17", "-O2", "-o", solver] + SOLVER_SRC, {}))
        for argv, env in steps:
            rc, out = sh(argv, wt, env, 900)
            if rc != 0:
                return "BUILD-FAIL", {}, f"{' '.join(argv[:2])} -> {rc}: {out[-300:]}"
        res = {}
        for t in tests:
            argv, env, to = TESTS[t]
            argv = [a.format(py=PY, solver=solver) for a in argv]
            rc, _ = sh(argv, wt, env, to)
            res[t] = "timeout" if rc == "timeout" else ("survived" if rc == 0 else "killed")
        return "ok", res, ""
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", wt], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)


def main():
    ap = argparse.ArgumentParser(description="Local only, never in CI.")
    ap.add_argument("--catalogue", default=os.path.join(ROOT, "tools/mutants/catalogue.json"))
    ap.add_argument("--only")
    ap.add_argument("--tests")
    ap.add_argument("--out")
    a = ap.parse_args()

    print("Local only, never in CI.")
    global BASE
    BASE = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    print("base commit", BASE)
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True):
        sys.exit("tracked files are dirty; commit or stash first")
    cat = json.load(open(a.catalogue))
    if a.only:
        ids = a.only.split(",")
        cat = [m for m in cat if m["id"] in ids]
        missing = set(ids) - {m["id"] for m in cat}
        if missing:
            sys.exit(f"unknown mutant ids: {sorted(missing)}")
    tests = list(TESTS) if a.tests is None else [t for t in a.tests.split(",") if t]
    bad = [t for t in tests if t not in TESTS]
    if bad:
        sys.exit(f"unknown tests: {bad}")

    out = a.out or tempfile.mkdtemp(prefix="mutants-out-")
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="mutants-wt-")
    before, t0, rows, fails = snapshot(), time.time(), [], []
    try:
        for m in cat:
            status, res, note = run_mutant(m, tests, tmp)
            killed = {t for t, r in res.items() if r != "survived"}
            expect = set(m.get("expect", []))
            problems = []
            if status != "ok":
                problems.append(f"{status}: {note}")
            else:
                missed = sorted(expect - killed)  # a test not run counts as missed
                if missed:
                    problems.append(f"expected kill missed: {missed}")
                if not expect and killed:
                    problems.append(f"known survivor was killed by {sorted(killed)}")
            extra = sorted(killed - expect) if expect else []
            fails += [f"{m['id']}: {p}" for p in problems]
            rows.append({"id": m["id"], "file": m["file"], "what": m.get("what", ""), "status": status,
                         "results": res, "expect": sorted(expect), "extra_kills": extra, "problems": problems})
            print(f"{m['id']}: {status} killed={sorted(killed)} {'FAIL' if problems else 'ok'}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # only the temp dir this run created
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
    wall = time.time() - t0

    md = [f"# Mutation matrix (wall {wall:.0f}s, base {BASE[:7]})", "", "| mutant | status | " + " | ".join(tests) + " | extra kills |",
          "|---|---|" + "---|" * (len(tests) + 1)]
    for r in rows:
        md.append(f"| {r['id']} | {r['status']} | " + " | ".join(r["results"].get(t, "-") for t in tests)
                  + f" | {','.join(r['extra_kills'])} |")
    if fails:
        md += ["", "Failures:"] + [f"- {f}" for f in fails]
    open(os.path.join(out, "matrix.md"), "w").write("\n".join(md) + "\n")
    json.dump({"wall_seconds": wall, "tests": tests, "mutants": rows, "failures": fails},
              open(os.path.join(out, "matrix.json"), "w"), indent=1)
    print("\n".join(md))
    print(f"matrix written to {out}")

    after = snapshot()
    import difflib
    ours = "mutants-wt-" in after[1]
    tracked = lambda t: [l for l in t.splitlines() if not l.startswith("??")]
    if tracked(after[0]) != tracked(before[0]) or ours:
        print("FATAL: tracked files or our worktrees changed during the run", file=sys.stderr)
        sys.exit(2)
    for name, i in (("status", 0), ("worktree list", 1)):
        d = [l for l in difflib.unified_diff(before[i].splitlines(), after[i].splitlines(), lineterm="", n=0)
             if l[0] in "+-" and l[:3] not in ("+++", "---")]
        if d:
            print(f"note: {name} changed by another process during the run (tolerated):", *d, sep="\n  ")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
