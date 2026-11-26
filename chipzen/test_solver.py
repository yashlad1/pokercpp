"""Self-check for the Chipzen solver.

Drives the compiled binary with scripted states. Catches the failures that
actually cost matches: folding a monster, calling off with air, and emitting
a raise outside the band the server accepts.

Run:  python3 chipzen/test_solver.py [path-to-solver]

Every check below is tagged:
  [invariant]  a rule that must hold whatever the constants are: legality,
               determinism, monotonicity, the stack cap.
  [pin]        pins fitted behaviour. It passes because of current constants
               (range steps, 0.85/0.82/0.90 realization, 0.50 open, 0.55 shove,
               0.62/0.30 bet edges). When a constant changes, a pin may need
               new numbers. That is expected, not a regression.
"""

import subprocess
import sys
import zlib

SOLVER = sys.argv[1] if len(sys.argv) > 1 else "/tmp/solver_check"


def ask(hole, board, pot, to_call, min_raise, max_raise, stack, bb, sims=3000,
        villain_raises=0):
    line = " ".join([
        str(len(hole)), *hole, str(len(board)), *board,
        str(pot), str(to_call), str(min_raise), str(max_raise),
        str(stack), str(bb), str(sims), str(villain_raises),
    ])
    # fixed nonzero seed per spot, derived from the spot so every run is identical
    line += " " + str(zlib.crc32(line.encode()) % 2147483646 + 1)
    out = subprocess.run([SOLVER], input=line + "\n", text=True,
                         capture_output=True, timeout=30)
    return out.stdout.strip()


def amount(reply):
    return int(reply.split()[1])


# [invariant]
r = ask(["As", "Ad"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r.startswith("raise"), f"AA preflop should raise, got {r!r}"

# [invariant]
assert 40 <= amount(r) <= 1000, f"raise out of band: {r!r}"

# [pin]
r = ask(["7h", "2c"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r == "fold", f"72o preflop should fold, got {r!r}"

# [pin]
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=150, min_raise=350,
        max_raise=900, stack=900, bb=20)
assert r == "fold", f"air facing a big bet should fold, got {r!r}"

# [invariant]
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=0, min_raise=50,
        max_raise=900, stack=900, bb=20)
assert r == "check", f"free card should be taken, got {r!r}"

# [pin]
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=200, max_raise=240,
        stack=240, bb=30)
assert r.startswith("raise") and amount(r) == 240, f"8bb AA should shove, got {r!r}"

# [invariant]
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=0, max_raise=0,
        stack=240, bb=30)
assert not r.startswith("raise"), f"raise emitted with no legal band: {r!r}"

# [invariant]
out = subprocess.run([SOLVER], input="garbage\n", text=True,
                     capture_output=True, timeout=30)
assert len(out.stdout.strip().splitlines()) == 1, "malformed input must get one reply"


SPOT = dict(board=[], pot=550, to_call=300, min_raise=800, max_raise=9700,
            stack=9700, bb=100)

# [pin]
loose = ask(["Kh", "Jd"], **SPOT, villain_raises=0)
tight = ask(["Kh", "Jd"], **SPOT, villain_raises=2)
assert loose != "fold", f"KJo should continue vs an unraised pot, got {loose!r}"
assert tight == "fold", f"KJo should fold vs a 3-bet, got {tight!r}"

# [invariant]
for raises in (0, 1, 2, 3):
    r = ask(["As", "Ad"], **SPOT, villain_raises=raises)
    assert r.startswith("raise"), f"AA should raise vs {raises} raises, got {r!r}"

# [invariant]
prev = None
for raises in (0, 1, 2, 3):
    r = ask(["9h", "8h"], **SPOT, villain_raises=raises)
    if prev == "fold":
        assert r == "fold", f"98s continued at {raises} raises after folding earlier"
    prev = r


CHECKED_TO = dict(pot=300, to_call=0, min_raise=20, max_raise=9000,
                  stack=9000, bb=100, villain_raises=1)

# [invariant]
r = ask(["As", "Ks"], ["Qs", "Js", "2s"], **CHECKED_TO)
assert r.startswith("raise"), f"a made flush should bet, got {r!r}"

# [pin]
air = [["7h", "2c"], ["8h", "3c"], ["9h", "4c"], ["6h", "2d"], ["5h", "3d"],
       ["8d", "2s"], ["7d", "3s"], ["9s", "2h"], ["6c", "3h"], ["5c", "2c"]]
bets = sum(ask(h, ["As", "Kd", "Qc"], **CHECKED_TO).startswith("raise") for h in air)
assert 0 < bets < len(air), f"bluffing should be mixed, bet {bets}/{len(air)}"

# [invariant]
once = ask(["7h", "2c"], ["As", "Kd", "Qc"], **CHECKED_TO)
twice = ask(["7h", "2c"], ["As", "Kd", "Qc"], **CHECKED_TO)
assert once == twice, f"bluff decision not deterministic: {once!r} vs {twice!r}"

# [invariant]
r = ask(["7h", "2c"], ["As", "Kd", "Qc"], pot=300, to_call=0, min_raise=20,
        max_raise=150, stack=150, bb=100, villain_raises=1)
if r.startswith("raise"):
    assert amount(r) <= 150, f"bet exceeds stack: {r!r}"


# A call that ends the betting has no later street to lose the pot on, so raw equity is the number against
# the price: 66 is ~52% raw, ~44% discounted, and the price is 45% in the all-in pin and 47.5% in the other two.
ENDS = dict(board=[], bb=100, villain_raises=1, sims=5000)

# [pin]
r = ask(["6s", "6d"], pot=1100, to_call=900, min_raise=0, max_raise=0, stack=900, **ENDS)
assert r == "call", f"all-in call with equity over the price should call, got {r!r}"

# [pin]
r = ask(["6s", "6d"], pot=840, to_call=760, min_raise=0, max_raise=0, stack=1900, **ENDS)
assert r == "call", f"call vs an all-in with equity over the price should call, got {r!r}"

# [pin]
r = ask(["6s", "6d"], pot=840, to_call=760, min_raise=1400, max_raise=1900, stack=1900, **ENDS)
assert r == "fold", f"discount must still apply while betting continues, got {r!r}"


OPEN = dict(board=[], pot=150, to_call=50, min_raise=200, bb=100, villain_raises=0, sims=5000)

# [pin]
r = ask(["Ks", "9h"], max_raise=9950, stack=9950, **OPEN)
assert r == "raise 250", f"K9o should open to 2.5bb, got {r!r}"

# [pin]
r = ask(["As", "Ad"], max_raise=9950, stack=9950, **OPEN)
assert r == "raise 250", f"AA should open to the same 2.5bb, got {r!r}"

# [pin]
r = ask(["7h", "2c"], max_raise=9950, stack=9950, **OPEN)
assert not r.startswith("raise"), f"72o is below 50% and should not open, got {r!r}"

# [pin]
r = ask(["Ks", "9h"], max_raise=750, stack=750, **OPEN)
assert r in ("fold", "raise 750"), f"8bb must shove or fold, not open to 2.5bb, got {r!r}"


# to_call above our stack: chips we cannot call set no price, so the report must decide exactly like
# to_call = stack with the pot cut by the excess.
CAP = dict(board=[], min_raise=0, max_raise=0, stack=400, bb=100, villain_raises=1, sims=5000)

# [invariant]
for hole, want in ((["As", "2h"], "call"), (["7s", "2h"], "fold"), (["As", "Ad"], "call")):
    capped = ask(hole, pot=600, to_call=400, **CAP)
    over = ask(hole, pot=10100, to_call=9900, **CAP)
    assert capped == want, f"{hole} capped spot should {want}, got {capped!r}"
    assert over == capped, f"{hole} over-stack report must match the capped spot {capped!r}, got {over!r}"

BOARD5 = ["Ks", "7c", "2d", "9h", "4s"]

# [pin]
r = ask(["Ah", "Kd"], BOARD5, pot=40, to_call=20, min_raise=40, max_raise=100,
        stack=100, bb=10)
assert r != "fold", f"top pair top kicker facing a small bet must not fold, got {r!r}"

# The 2.5bb open applies only when just the blind difference is owed. It would raise to 25, clamped up to
# min_raise, so a "raise 80" here can only come from the open path.
SPOT = dict(board=[], pot=50, to_call=40, min_raise=80, max_raise=1000, stack=1000, bb=10)
# [pin]
for hole in (["Ah", "Kd"], ["Qs", "Jd"], ["9h", "9d"], ["As", "5s"], ["Ks", "Td"]):
    r = ask(hole, villain_raises=0, **SPOT)
    assert r != "raise 80", f"{hole} to_call>=bb must skip the open path, got {r!r}"

# [pin]
r = ask(["2h", "7s"], ["7c", "Tc", "Ad"], pot=200, to_call=100, min_raise=9000,
        max_raise=9000, stack=9000, bb=100, villain_raises=1, sims=5000)
assert r == "fold", f"a pair of sevens vs a pot-size bet should fold to the narrowed range, got {r!r}"

print("solver self-check: all passed")
