"""Drive bot.py against the real SDK, without Docker or a server.

Catches API mismatches and illegal actions before the image is uploaded.
The check that matters is the last column: an action the server did not
offer is rejected on the wire, and a raise outside [min_raise, max_raise]
is rejected too.

Needs the SDK and the compiled engine:
    pip install chipzen-bot pybind11
    g++ -std=c++17 -O2 -shared -fPIC $(python -m pybind11 --includes) \
        chipzen/pokercpp_engine.cpp montecarlo/MonteCarloSimulator.cpp \
        model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp \
        -o chipzen/pokercpp_engine$(python3-config --extension-suffix)
    PYTHONPATH=chipzen python chipzen/test_bot_sdk.py
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("POKERCPP_SIMS", "5000")

from chipzen import Action, GameState
from chipzen.models import Card
import bot as botmod

B = botmod.PokerCppBot()

def C(s): return Card.from_str(s)

BLINDS = [
    {"seat": 0, "action": "post_small_blind", "amount": 10, "phase": "preflop", "is_timeout": False},
    {"seat": 1, "action": "post_big_blind",   "amount": 20, "phase": "preflop", "is_timeout": False},
]

SPOTS = [
    ("preflop AA facing 20",  dict(phase="preflop", hole_cards=[C("As"),C("Ad")], board=[],
        pot=30, to_call=20, min_raise=40, max_raise=1000, your_stack=1000,
        valid_actions=["fold","call","raise"])),
    ("preflop 72o facing 20", dict(phase="preflop", hole_cards=[C("7h"),C("2c")], board=[],
        pot=30, to_call=20, min_raise=40, max_raise=1000, your_stack=1000,
        valid_actions=["fold","call","raise"])),
    ("flop nut flush, checked to", dict(phase="flop", hole_cards=[C("As"),C("Ks")],
        board=[C("Qs"),C("Js"),C("2s")], pot=200, to_call=0, min_raise=20, max_raise=900,
        your_stack=900, valid_actions=["check","raise"])),
    ("river air facing big bet", dict(phase="river", hole_cards=[C("7h"),C("2c")],
        board=[C("Ah"),C("Kd"),C("Qc"),C("4s"),C("9h")], pot=200, to_call=150,
        min_raise=350, max_raise=900, your_stack=900, valid_actions=["fold","call","raise"])),
    ("no raise offered", dict(phase="river", hole_cards=[C("As"),C("Ad")],
        board=[C("Ah"),C("Kd"),C("Qc"),C("4s"),C("9h")], pot=200, to_call=50,
        min_raise=0, max_raise=0, your_stack=900, valid_actions=["fold","call"])),
    ("short stack 8bb AA", dict(phase="preflop", hole_cards=[C("As"),C("Ad")], board=[],
        pot=300, to_call=100, min_raise=200, max_raise=240, your_stack=240,
        valid_actions=["fold","call","raise"])),
    ("check-only spot", dict(phase="turn", hole_cards=[C("7h"),C("2c")],
        board=[C("Ah"),C("Kd"),C("Qc"),C("4s")], pot=100, to_call=0,
        min_raise=0, max_raise=0, your_stack=900, valid_actions=["check"])),
]

fails = 0
worst = 0.0
for name, kw in SPOTS:
    st = GameState(hand_number=1, dealer_seat=0, your_seat=1,
                   opponent_stacks=[1000], action_history=list(BLINDS), **kw)
    t0 = time.monotonic()
    act = B.decide(st)
    ms = (time.monotonic() - t0) * 1000
    worst = max(worst, ms)

    ok = act.action in kw["valid_actions"]
    detail = ""
    if act.action == "raise":
        lo, hi = kw["min_raise"], kw["max_raise"]
        if not (lo <= act.amount <= hi):
            ok = False
            detail = f" OUT OF BAND [{lo},{hi}]"
        detail = f" to {act.amount}" + detail
    if not ok:
        fails += 1
    print(f"  {name:32s} -> {act.action}{detail:22s} {ms:6.1f}ms  {'ok' if ok else 'ILLEGAL'}")

print()
print(f"worst decision latency: {worst:.1f} ms  (ranked budget 2000 ms)")
print("ILLEGAL ACTIONS FOUND" if fails else "all actions legal")
sys.exit(1 if fails else 0)
