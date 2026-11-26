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
# Monsters get money in, never folded.
r = ask(["As", "Ad"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r.startswith("raise"), f"AA preflop should raise, got {r!r}"

# [invariant]
# ...and the raise respects the server's band.
assert 40 <= amount(r) <= 1000, f"raise out of band: {r!r}"

# [pin]
# Trash folds to a real price.
r = ask(["7h", "2c"], [], pot=30, to_call=20, min_raise=40, max_raise=1000, stack=1000, bb=20)
assert r == "fold", f"72o preflop should fold, got {r!r}"

# [pin]
# Trash on a board that missed it folds to a big bet.
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=150, min_raise=350,
        max_raise=900, stack=900, bb=20)
assert r == "fold", f"air facing a big bet should fold, got {r!r}"

# [invariant]
# Folding is never right when checking is free.
r = ask(["7h", "2c"], ["Ah", "Kd", "Qc"], pot=200, to_call=0, min_raise=50,
        max_raise=900, stack=900, bb=20)
assert r == "check", f"free card should be taken, got {r!r}"

# [pin]
# Short stack with a monster shoves rather than nursing the stack.
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=200, max_raise=240,
        stack=240, bb=30)
assert r.startswith("raise") and amount(r) == 240, f"8bb AA should shove, got {r!r}"

# [invariant]
# Raising illegal (both bounds zero) must not produce a raise.
r = ask(["As", "Ad"], [], pot=300, to_call=100, min_raise=0, max_raise=0,
        stack=240, bb=30)
assert not r.startswith("raise"), f"raise emitted with no legal band: {r!r}"

# [invariant]
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

# [pin]
loose = ask(["Kh", "Jd"], **SPOT, villain_raises=0)
tight = ask(["Kh", "Jd"], **SPOT, villain_raises=2)
assert loose != "fold", f"KJo should continue vs an unraised pot, got {loose!r}"
assert tight == "fold", f"KJo should fold vs a 3-bet, got {tight!r}"

# [invariant]
# Aces do not care what the opponent represents.
for raises in (0, 1, 2, 3):
    r = ask(["As", "Ad"], **SPOT, villain_raises=raises)
    assert r.startswith("raise"), f"AA should raise vs {raises} raises, got {r!r}"

# [invariant]
# Narrowing the range can only ever reduce a marginal hand's willingness to
# continue, never increase it.
prev = None
for raises in (0, 1, 2, 3):
    r = ask(["9h", "8h"], **SPOT, villain_raises=raises)
    if prev == "fold":
        assert r == "fold", f"98s continued at {raises} raises after folding earlier"
    prev = r

# --- bluffing -------------------------------------------------------------
#
# Betting must be polarised: strong hands and hopeless ones, never the
# middle. A hand with showdown value loses it by betting - it folds out what
# it beats and gets called by what beats it.

CHECKED_TO = dict(pot=300, to_call=0, min_raise=20, max_raise=9000,
                  stack=9000, bb=100, villain_raises=1)

# [invariant]
# The nuts always bets.
r = ask(["As", "Ks"], ["Qs", "Js", "2s"], **CHECKED_TO)
assert r.startswith("raise"), f"a made flush should bet, got {r!r}"

# [pin]
# Bluffing has to be a frequency, not a rule. If every hopeless hand bets,
# it is readable; if none does, the bot can only ever win with the best hand.
air = [["7h", "2c"], ["8h", "3c"], ["9h", "4c"], ["6h", "2d"], ["5h", "3d"],
       ["8d", "2s"], ["7d", "3s"], ["9s", "2h"], ["6c", "3h"], ["5c", "2c"]]
bets = sum(ask(h, ["As", "Kd", "Qc"], **CHECKED_TO).startswith("raise") for h in air)
assert 0 < bets < len(air), f"bluffing should be mixed, bet {bets}/{len(air)}"

# [invariant]
# The same spot must always resolve the same way, or nothing is reproducible.
once = ask(["7h", "2c"], ["As", "Kd", "Qc"], **CHECKED_TO)
twice = ask(["7h", "2c"], ["As", "Kd", "Qc"], **CHECKED_TO)
assert once == twice, f"bluff decision not deterministic: {once!r} vs {twice!r}"

# [invariant]
# A bet must never be larger than the stack behind it.
r = ask(["7h", "2c"], ["As", "Kd", "Qc"], pot=300, to_call=0, min_raise=20,
        max_raise=150, stack=150, bb=100, villain_raises=1)
if r.startswith("raise"):
    assert amount(r) <= 150, f"bet exceeds stack: {r!r}"

# --- calls that end the betting -------------------------------------------
#
# Equity is discounted on the way to a call because a later street can cost
# us the pot. A call that ends the betting has no later street to lose it on:
# the cards just run out, so raw equity is the right number against the price.
# 66 has ~52% against the range but only ~44% once discounted (0.85). The price
# is 45% in the all-in pin and 47.5% in the other two, so the discounted number
# would fold in all three.

ENDS = dict(board=[], bb=100, villain_raises=1, sims=5000)

# [pin]
# The call puts us all-in.
r = ask(["6s", "6d"], pot=1100, to_call=900, min_raise=0, max_raise=0, stack=900, **ENDS)
assert r == "call", f"all-in call with equity over the price should call, got {r!r}"

# [pin]
# The opponent is all-in and we cover: raising is closed, so the call ends it.
r = ask(["6s", "6d"], pot=840, to_call=760, min_raise=0, max_raise=0, stack=1900, **ENDS)
assert r == "call", f"call vs an all-in with equity over the price should call, got {r!r}"

# [pin]
# Control: same price, but raising is open and chips are behind. The betting
# goes on, the discount still applies, and the same hand folds.
r = ask(["6s", "6d"], pot=840, to_call=760, min_raise=1400, max_raise=1900, stack=1900, **ENDS)
assert r == "fold", f"discount must still apply while betting continues, got {r!r}"

# --- opening from the small blind ------------------------------------------
#
# Limping hands the big blind the initiative; an open takes it. A hand that
# beats a random one more often than not (K9o is ~59%) opens to 2.5bb, and
# AA opens to the same size so the raise says nothing about the hand.
# Below 50% it stays out of the raise. At 10bb or less the shove-or-fold
# rule decides, so there is no 2.5bb open.

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

# --- a bet bigger than our stack ---------------------------------------------
#
# The platform may report a to_call above our stack. We can only call what we
# have; the excess goes back to the bettor. Chips we can't call can't be won
# or lost, so they must not set the price: the report must be decided exactly
# like to_call = stack with the pot cut by the excess. A2o has the equity to
# call 400 into 600 as the big blind, but not the 9900-into-10100 the raw
# report implies.

CAP = dict(board=[], min_raise=0, max_raise=0, stack=400, bb=100, villain_raises=1, sims=5000)

# [invariant] over == capped; the expected words (`want`) are pins
for hole, want in ((["As", "2h"], "call"), (["7s", "2h"], "fold"), (["As", "Ad"], "call")):
    capped = ask(hole, pot=600, to_call=400, **CAP)
    over = ask(hole, pot=10100, to_call=9900, **CAP)
    assert capped == want, f"{hole} capped spot should {want}, got {capped!r}"
    assert over == capped, f"{hole} over-stack report must match the capped spot {capped!r}, got {over!r}"

# --- short-stack shove, open path, and bet sizing ----------------------------
#
# A1: shoving when checked to at 10bb or less is deliberate: a 5x-pot overbet,
# right vs callers and wrong vs folders; sizing by opponent type is planned.
BOARD5 = ["Ks", "7c", "2d", "9h", "4s"]

# [pin]
# Facing a bet at 10bb a shove is still allowed; only demand it is not a fold.
r = ask(["Ah", "Kd"], BOARD5, pot=40, to_call=20, min_raise=40, max_raise=100,
        stack=100, bb=10)
assert r != "fold", f"top pair top kicker facing a small bet must not fold, got {r!r}"

# A2: the 2.5bb open applies only when just the blind difference is owed. A
# full bb or more to call with villain_raises=0 must not open. The open would
# raise to 2.5bb = 25, clamped up to min_raise, so the tell is "raise 80". None
# of these hands reaches 80 by equity (all call or fold once the guard is on),
# so a raise 80 here can only come from the open path.
SPOT = dict(board=[], pot=50, to_call=40, min_raise=80, max_raise=1000, stack=1000, bb=10)
# [pin]
for hole in (["Ah", "Kd"], ["Qs", "Jd"], ["9h", "9d"], ["As", "5s"], ["Ks", "Td"]):
    r = ask(hole, villain_raises=0, **SPOT)
    assert r != "raise 80", f"{hole} to_call>=bb must skip the open path, got {r!r}"

# [pin]
# B: the bet is sized against the pot before it. Pot 200 with 100 to call is a
# pot-size bet (fraction 1.0): the credited range narrows, and 7s on A-T-7 (a
# pair under the ace) is no longer worth 100 to win 300.
r = ask(["2h", "7s"], ["7c", "Tc", "Ad"], pot=200, to_call=100, min_raise=9000,
        max_raise=9000, stack=9000, bb=100, villain_raises=1, sims=5000)
assert r == "fold", f"a pair of sevens vs a pot-size bet should fold to the narrowed range, got {r!r}"

print("solver self-check: all passed")
