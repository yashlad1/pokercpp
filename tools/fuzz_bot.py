"""Fuzz PokerCppBot.decide with 5,000 random GameStates.

usage: python tools/fuzz_bot.py <path to a chipzen/ folder>
Prints counts of exceptions, illegal actions and fallbacks (ENGINE FAILED
logs); exits 1 if any is non-zero.
"""
import io
import logging
import os
import random
import sys

os.environ["POKERCPP_SIMS"] = "300"
sys.path.insert(0, os.path.abspath(sys.argv[1]))
import bot  # noqa: E402
from chipzen import Card, GameState  # noqa: E402

buf = io.StringIO()
log = logging.getLogger("pokercpp")
log.addHandler(logging.StreamHandler(buf))
log.setLevel(logging.ERROR)

DECK = [r + s for r in "23456789TJQKA" for s in "shdc"]
SETS = [["check", "raise"], ["check"], ["fold", "call"], ["fold", "call", "raise"],
        ["fold", "call", "all_in"], ["fold", "all_in"], ["check", "all_in"],
        ["fold", "call", "raise", "all_in"]]
rng = random.Random(1)
b = bot.PokerCppBot()
exc = illegal = fallback = inverted = 0
for k in range(5000):
    if k % 200 == 0:
        b.on_match_start(rng.choice([{}, None, {"game_config": {
            "big_blind": rng.choice([20, 100]), "ante": rng.choice([0, 0, 5])}}]))
    ph = rng.choice(["preflop", "flop", "turn", "river"])
    cs = rng.sample(DECK, 2 + {"preflop": 0, "flop": 3, "turn": 4, "river": 5}[ph])
    stack = rng.choice([0, 1, 3, 50, 500, 5000, rng.randint(1, 20000)])
    pot = rng.choice([0, 1, 15, 300, rng.randint(0, 30000)])
    va = rng.choice(SETS)
    tc = 0 if "check" in va else rng.choice([1, 5, 50, stack, stack + 500, rng.randint(1, 20000)])
    if "raise" in va:
        lo = rng.randint(1, max(1, stack))
        hi = max(lo, stack + rng.choice([0, 0, 5]))
        lo = min(lo, hi)
        if rng.random() < .2:
            lo = hi
        elif rng.random() < .2:  # short stack: min_raise above max_raise (= stack)
            hi = max(stack, 1)
            lo = hi + rng.randint(1, 5000)
    else:
        lo = hi = 0
    hist = []
    if ph == "preflop" and rng.random() < .5:
        hist = [{"seat": 0, "action": "post_small_blind", "amount": 50},
                {"seat": 1, "action": "post_big_blind", "amount": 100}]
    for _ in range(rng.randint(0, 3)):
        hist.append({"seat": rng.choice([0, 1]), "action": rng.choice(["raise", "all_in", "call", "check", "bet"]),
                     "amount": rng.randint(1, 500)})
    st = GameState(
        hand_number=rng.choice([0, 0, k // 5, k // 5, rng.randint(0, 50)]), phase=ph,
        hole_cards=[Card(c[0], c[1]) for c in cs[:2]], board=[Card(c[0], c[1]) for c in cs[2:]],
        pot=pot, your_stack=stack, your_seat=rng.choice([0, 1]),
        dealer_seat=rng.choice([0, 1, None]), to_call=tc, min_raise=lo, max_raise=hi,
        valid_actions=va, action_history=hist)
    inverted += lo > hi
    if rng.random() < .02:
        b.on_round_start({})
    buf.truncate(0)
    buf.seek(0)
    try:
        a = b.decide(st)
    except Exception:
        exc += 1
        continue
    fallback += "ENGINE FAILED" in buf.getvalue()
    if a.action not in va or (a.action == "raise" and not (lo <= a.amount <= hi or (lo > hi and a.amount == hi))):
        illegal += 1
print(f"exceptions={exc} illegal={illegal} fallbacks={fallback} min_gt_max={inverted}")
sys.exit(1 if exc or illegal or fallback else 0)
