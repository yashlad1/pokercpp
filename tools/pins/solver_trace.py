"""Run chipzen/test_solver.py unchanged and print every solver call: the input
line, then the reply. Pins the solver CLI's output on the test's own inputs.

    python solver_trace.py <solver_binary> <path/to/test_solver.py>
"""
import runpy
import subprocess
import sys

solver, test = sys.argv[1], sys.argv[2]
real = subprocess.run


def traced(*a, **kw):
    r = real(*a, **kw)
    print("IN  ", repr(kw.get("input")))
    print("OUT ", repr(r.stdout), "rc", r.returncode, "err", repr(r.stderr))
    return r


subprocess.run = traced
sys.argv = [test, solver]
runpy.run_path(test, run_name="__main__")
