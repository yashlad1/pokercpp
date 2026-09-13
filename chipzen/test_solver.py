"""Self-check for the Chipzen solver.

Drives the compiled binary with scripted states. Catches the failures that
actually cost matches: folding a monster, calling off with air, and emitting
a raise outside the band the server accepts.

Run:  python3 chipzen/test_solver.py [path-to-solver]
"""

import subprocess
import sys

SOLVER = sys.argv[1] if len(sys.argv) > 1 else "/tmp/solver_check"


def ask(hole, board, pot, to_call, min_raise, max_raise, stack, bb, sims=3000,
        villain_raises=0):
    line = " ".join([
        str(len(hole)), *hole, str(len(board)), *board,
        str(pot), str(to_call), str(min_raise), str(max_raise),
        str(stack), str(bb), str(sims), str(villain_raises),
    ])
    out = subprocess.run([SOLVER], input=line + "\n", text=True,
                         capture_output=True, timeout=30)
    return out.stdout.strip()


def amount(reply):
    return int(reply.split()[1])


# Monsters get money in, never folded.
r = ask(["As", "Ad"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r.startswith("raise"), f"AA preflop should raise, got {r!r}"

# ...and the raise respects the server's band.
assert 40 <= amount(r) <= 1000, f"raise out of band: {r!r}"

# Trash folds to a real price.
r = ask(["7h", "2c"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r == "fold", f"72o preflop should fold, got {r!r}"

# Trash on a board that missed it folds to a big bet.
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=150, min_raise=350,
        max_raise=900, stack=900, bb=20)
assert r == "fold", f"air facing a big bet should fold, got {r!r}"

# Folding is never right when checking is free.
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=0, min_raise=50,
        max_raise=900, stack=900, bb=20)
assert r == "check", f"free card should be taken, got {r!r}"

# Short stack with a monster shoves rather than nursing the stack.
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=200, max_raise=240,
        stack=240, bb=30)
assert r.startswith("raise") and amount(r) == 240, f"8bb AA should shove, got {r!r}"

# Raising illegal (both bounds zero) must not produce a raise.
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=0, max_raise=0,
        stack=240, bb=30)
assert not r.startswith("raise"), f"raise emitted with no legal band: {r!r}"

# A malformed line still gets exactly one reply, so the caller never blocks.
out = subprocess.run([SOLVER], input="garbage\n", text=True,
                     capture_output=True, timeout=30)
assert len(out.stdout.strip().splitlines()) == 1, "malformed input must get one reply"

# --- opponent range -------------------------------------------------------
#
# The whole point of modelling a range is that the same hand at the same
# price becomes a fold once the opponent has shown strength. If these two
# ever agree, the range is not reaching the decision.

SPOT = dict(board=[], pot=550, to_call=300, min_raise=800, max_raise=9700,
            stack=9700, bb=100)

loose = ask(["Kh", "Jd"], **SPOT, villain_raises=0)
tight = ask(["Kh", "Jd"], **SPOT, villain_raises=2)
assert loose != "fold", f"KJo should continue vs an unraised pot, got {loose!r}"
assert tight == "fold", f"KJo should fold vs a 3-bet, got {tight!r}"

# Aces do not care what the opponent represents.
for raises in (0, 1, 2, 3):
    r = ask(["As", "Ad"], **SPOT, villain_raises=raises)
    assert r.startswith("raise"), f"AA should raise vs {raises} raises, got {r!r}"

# Narrowing the range can only ever reduce a marginal hand's willingness to
# continue, never increase it.
prev = None
for raises in (0, 1, 2, 3):
    r = ask(["9h", "8h"], **SPOT, villain_raises=raises)
    if prev == "fold":
        assert r == "fold", f"98s continued at {raises} raises after folding earlier"
    prev = r

print("solver self-check: all passed")
