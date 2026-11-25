"""Black-box test for the live Chipzen blind schedule in tools/match.py.
Run from the repo root: PYTHONPATH=chipzen python tools/test_match.py"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
fails = []


def check(case, h, expected, fn):
    try:
        got = fn()
    except Exception as e:
        got = "%s: %s" % (type(e).__name__, e)
    if got != expected:
        fails.append(case)
        print("FAIL %s h=%s expected=%s got=%s" % (case, h, expected, got))


try:
    import match
except Exception as e:
    match = None
    fails.append("import")
    print("FAIL import match: %s: %s" % (type(e).__name__, e))

if match is not None:
    # 1. default mode, before any global is touched
    live = [100, 100, 150, 150, 200, 200, 300, 300, 400, 400, 600, 600, 800, 800]
    for h, bb in zip([1, 20, 21, 40, 41, 60, 61, 80, 81, 100, 101, 120, 121, 140], live):
        check("default", h, (bb // 2, bb), lambda: tuple(match.blinds_for(h)))

    saved = (getattr(match, "FIRST_BB", None), getattr(match, "DOUBLE_EVERY", None))
    try:
        # 2. doubling mode
        match.FIRST_BB, match.DOUBLE_EVERY = 100, 25
        for h, bb in [(25, 100), (26, 200)]:
            check("double25", h, (bb // 2, bb), lambda: tuple(match.blinds_for(h)))
        # 3. first bb 50, live steps
        match.FIRST_BB, match.DOUBLE_EVERY = 50, None
        check("first_bb50", 21, (37, 75), lambda: tuple(match.blinds_for(21)))
    except Exception as e:
        fails.append("globals")
        print("FAIL setting globals: %s: %s" % (type(e).__name__, e))
    finally:
        match.FIRST_BB, match.DOUBLE_EVERY = saved

# 4. smoke
env = dict(os.environ, PYTHONPATH="chipzen")
r = subprocess.run([sys.executable, "tools/match.py", "--matches", "2", "--vs", "nit",
                    "--hand-cap", "60"], cwd=ROOT, env=env, capture_output=True, text=True)
for case, ok, exp in [("smoke exit", r.returncode == 0, "exit 0"),
                      ("smoke Schedule:", "Schedule:" in r.stdout, "present"),
                      ("smoke ASSUMED", "ASSUMED" not in r.stdout, "absent")]:
    if not ok:
        fails.append(case)
        print("FAIL %s h=- expected=%s got=rc=%s stderr=%s" % (case, exp, r.returncode, r.stderr[-300:]))

print("FAIL: %d case(s)" % len(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
