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


# An opponent who raises every hand is not showing a strong hand when they
# raise. The bot remembers, across the match, how often this opponent has
# raised, and widens the range it puts them on to match. K8o is a fold against
# a shove from a tight range and a call against a shove from any two cards.
BL = [
    {"seat": 0, "action": "post_small_blind", "amount": 50,  "phase": "preflop", "is_timeout": False},
    {"seat": 1, "action": "post_big_blind",   "amount": 100, "phase": "preflop", "is_timeout": False},
]
SHOVE = BL + [{"seat": 0, "action": "raise", "amount": 1500, "phase": "preflop", "is_timeout": False}]
LIMP  = BL + [{"seat": 0, "action": "call",  "amount": 50,   "phase": "preflop", "is_timeout": False}]

def shove_spot(n, hole):
    return GameState(hand_number=n, dealer_seat=0, your_seat=1, opponent_stacks=[0],
        action_history=list(SHOVE), phase="preflop", hole_cards=[C(hole[:2]), C(hole[2:])],
        board=[], pot=1600, to_call=1400, min_raise=0, max_raise=0, your_stack=1400,
        valid_actions=["fold", "call"])

def limp_spot(n, hole):
    return GameState(hand_number=n, dealer_seat=0, your_seat=1, opponent_stacks=[1400],
        action_history=list(LIMP), phase="preflop", hole_cards=[C(hole[:2]), C(hole[2:])],
        board=[], pot=200, to_call=0, min_raise=200, max_raise=1400, your_stack=1400,
        valid_actions=["check", "raise"])

H = "Ks8h"
extra = 0

def check(cond, msg):
    global extra
    if not cond:
        extra += 1
        print("FAIL:", msg)

b = botmod.PokerCppBot()
check(b.decide(shove_spot(1, H)).action == "fold", "fresh bot should fold K8o to a shove")

b = botmod.PokerCppBot()
for n in range(1, 21):
    b.decide(shove_spot(n, "7h2c"))
check(b.decide(shove_spot(21, H)).action == "call",
      "after 20 shove hands the bot should call K8o: a constant shover has a wide range")

b2 = botmod.PokerCppBot()
for n in range(1, 21):
    b2.decide(limp_spot(n, "7h2c"))
check(b2.decide(shove_spot(21, H)).action == "fold",
      "after 20 passive hands a shove is still strong: K8o folds")

b.on_match_start({})
check(b.decide(shove_spot(22, H)).action == "fold",
      "on_match_start must clear the memory: K8o folds again")

print("opponent-memory checks:", "FAILED" if extra else "ok")

# The platform's own fixture sends no blinds in the history, so the bot has to
# work the big blind out from its first preflop decision, and an all-in is
# sometimes the only way to call or to raise.
extra_before = extra

def wire(hist, **kw):
    kw.setdefault("hand_number", 1)
    kw.setdefault("phase", "preflop")
    kw.setdefault("board", [])
    kw.setdefault("opponent_stacks", [1000])
    kw["hole_cards"] = [C(kw["hole_cards"][:2]), C(kw["hole_cards"][2:])]
    return GameState(action_history=hist, **kw)

# 1. Small blind, empty history: pot 15 + to_call 5 gives a 10 chip big blind,
# so the open is 2.5 big blinds, a raise to 25.
b = botmod.PokerCppBot()
b.on_match_start({"game_config": {"small_blind": 5, "big_blind": 10, "ante": 0,
                                  "starting_stack": 1000}})
a = b.decide(wire([], hole_cards="AhKd", your_seat=0, dealer_seat=0, pot=15,
                  to_call=5, min_raise=20, max_raise=995, your_stack=995,
                  valid_actions=["fold", "call", "raise"]))
check(a.action == "raise" and a.amount == 25,
      f"small blind, empty history: AKo should open to 25, got {a.action} {a.amount}")

# 2. Big blind, empty history, no match_start fallback: (pot 40 - to_call 20) / 2
# is a 10 chip big blind, so 70 behind is 7 big blinds and AA shoves.
b = botmod.PokerCppBot()
a = b.decide(wire([], hole_cards="AhAd", your_seat=1, dealer_seat=0, pot=40,
                  to_call=20, min_raise=50, max_raise=80, your_stack=70,
                  valid_actions=["fold", "call", "raise"]))
check(a.action == "all_in" or (a.action == "raise" and a.amount == 80),
      f"big blind, empty history, 7bb deep: AA should shove, got {a.action} {a.amount}")

# 3. Only all_in offered: wanting to raise means sending all_in.
b = botmod.PokerCppBot()
a = b.decide(wire(list(BL), hole_cards="AhAd", your_seat=0, dealer_seat=0, pot=150,
                  to_call=50, min_raise=0, max_raise=0, your_stack=700,
                  valid_actions=["fold", "call", "all_in"]))
check(a.action == "all_in", f"only all_in raises: AA should all_in, got {a.action}")

# 4. The call is offered as all_in (the opponent's shove covers our stack).
b = botmod.PokerCppBot()
a = b.decide(wire(BL + [{"seat": 0, "action": "all_in", "amount": 1500,
                         "phase": "preflop", "is_timeout": False}],
                  hole_cards="AhAd", your_seat=1, dealer_seat=0, pot=1600,
                  to_call=1400, min_raise=0, max_raise=0, your_stack=900,
                  valid_actions=["fold", "all_in"]))
check(a.action == "all_in", f"call offered only as all_in: AA must not fold, got {a.action}")
print("wire-adapter checks:", "FAILED" if extra > extra_before else "ok")

print()
print(f"worst decision latency: {worst:.1f} ms  (ranked budget 2000 ms)")
print("ILLEGAL ACTIONS FOUND" if fails else "all actions legal")
sys.exit(1 if fails or extra else 0)
