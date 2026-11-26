"""Match mode: full freezeout matches with rising blinds, scored by match wins.

Default schedule = the live Chipzen one (observed in 7 matches, issue #13): 100 bb
stack, the big blind steps every 20 hands 100/150/200/300/400/600/800. --double-every N
selects the old doubling-from-the-start-bb schedule instead.

Each match is played twice with the same per-hand seeds and the seats swapped
(the other agent holds the button first), so card luck cancels within a pair.

    python tools/match.py --matches 200 --vs maniac [--hand-cap 1000] [--sims 2000] [--seed0 1]
"""

import argparse
import math
import sys

from bench import OPPONENTS, Bot, PokerCpp, play_hand, split_roles

START_BB, FIRST_BB, DOUBLE_EVERY = 100, 100, None  # stack in bb, big blind, hands per doubling (None = live steps)


def blinds_for(hand_no):
    if DOUBLE_EVERY:
        bb = FIRST_BB * 2 ** ((hand_no - 1) // DOUBLE_EVERY)
    else:
        # ponytail: levels past 140 (index 7+) are extrapolated (each pair doubles), never observed live
        k = (hand_no - 1) // 20
        bb = FIRST_BB * 2 ** (k // 2) * (3 if k % 2 else 2) // 2
    return (bb // 2, bb)


def play_match(match_seed, agents, hand_cap=1000):
    """agents[0] has the button on hand 1. Returns (index of winner, hands)."""
    split_roles(*agents)
    stacks = [START_BB * FIRST_BB] * 2
    hand_no = 0
    while min(stacks) > 0 and hand_no < hand_cap:
        hand_no += 1
        f = hand_no % 2 == 0  # button alternates: swap agent order and stack order
        order = (1, 0) if f else (0, 1)
        d = play_hand(match_seed * 1000 + hand_no, [agents[i] for i in order],
                      blinds_for(hand_no), stacks=[stacks[i] for i in order])
        for seat, i in enumerate(order):
            stacks[i] += d[seat]
    # level chips at the cap: the agent seated first in this match wins (Chipzen rule)
    return (1 if stacks[1] > stacks[0] else 0), hand_no


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def run(opp_name, matches, hand_cap, sims, seed0, hero="engine"):
    # bot: a fresh chipzen/bot.py per match, so its memory starts empty every match
    new_hero = ((lambda: Bot(FIRST_BB // 2, FIRST_BB, START_BB * FIRST_BB, sims)) if hero == "bot"
                else (lambda: PokerCpp(sims=sims)))
    pair = [0, 0, 0]  # lost both, split, won both
    wins = hands = 0
    for m in range(matches):
        ms = seed0 + m
        h1 = (new_hero(), OPPONENTS[opp_name]())
        w1, n1 = play_match(ms, h1, hand_cap)       # hero on the button first
        v2 = (OPPONENTS[opp_name](), new_hero())
        w2, n2 = play_match(ms, v2, hand_cap)       # villain on the button first
        won = [w1 == 0, w2 == 1]
        wins += sum(won)
        hands += n1 + n2
        pair[sum(won)] += 1
    n = 2 * matches
    lo, hi = wilson(wins, n)
    print(f"vs {opp_name:12s} {wins}/{n} = {wins / n:.1%} [{lo:.1%}, {hi:.1%}]   "
          f"pairs lost both {pair[0]} / split {pair[1]} / won both {pair[2]}   "
          f"avg {hands / n:.1f} hands/match")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", type=int, default=200, help="duplicate pairs (2 matches each)")
    ap.add_argument("--vs", default="all", choices=[*OPPONENTS, "all"])
    ap.add_argument("--hand-cap", type=int, default=1000)
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--hero", default="engine", choices=["engine", "bot"],
                    help="engine: call the C++ engine directly; bot: run chipzen/bot.py")
    ap.add_argument("--start-bb", type=int, default=FIRST_BB, help="first big blind (stack is 100 of them)")
    ap.add_argument("--double-every", type=int, help="double the bb every N hands (default: live Chipzen steps)")
    a = ap.parse_args()
    FIRST_BB, DOUBLE_EVERY = a.start_bb, a.double_every
    sched = f"doubling every {DOUBLE_EVERY} hands" if DOUBLE_EVERY else "live Chipzen steps every 20 hands"
    print(f"Schedule: {START_BB} bb start, bb {FIRST_BB}, {sched}, no antes, hand cap {a.hand_cap}", flush=True)
    for nm in (list(OPPONENTS) if a.vs == "all" else [a.vs]):
        run(nm, a.matches, a.hand_cap, a.sims, a.seed0, a.hero)
        sys.stdout.flush()
