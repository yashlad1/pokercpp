"""Black-box test for B4 (#63, H-6): the Monte Carlo seed is keyed on the deal,
not a global hand counter. Run from the repo root:
PYTHONPATH=chipzen python tools/test_seed_key.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench
import match

SIMS = 200
fails = []


def case(name, fn):
    try:
        ok = fn()
    except Exception as e:
        ok = False
        print("  exception: %s: %s" % (type(e).__name__, e))
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    if not ok:
        fails.append(name)


def inserted_hand(opp):
    def run():
        r1 = bench.duplicate_match(20, bench.PokerCpp(sims=SIMS, memory=False),
                                   bench.OPPONENTS[opp](), seed0=1)
        r2 = bench.duplicate_match(22, bench.PokerCpp(sims=SIMS, memory=False),
                                   bench.OPPONENTS[opp](), seed0=0)
        return list(r2[1:]) == list(r1)
    return run


def run_to_run():
    def go():
        return bench.duplicate_match(10, bench.PokerCpp(sims=SIMS),
                                     bench.OPPONENTS["reference"](), seed0=3)
    return list(go()) == list(go())


def record(play):
    """Run play(); return {id(agent): [seeds]} and the original-order list of agents."""
    seeds = {}
    orig = bench.pokercpp_engine.decide

    def wrapper(*a, **kw):
        who = sys._getframe(1).f_locals.get("self")
        seeds.setdefault(id(who), []).append(kw["seed"])
        return orig(*a, **kw)

    bench.pokercpp_engine.decide = wrapper
    try:
        play()
    finally:
        bench.pokercpp_engine.decide = orig
    return seeds


def match_mode():
    def go():
        hero = bench.PokerCpp(sims=SIMS)
        out = []
        seeds = record(lambda: out.append(match.play_match(
            7, [hero, bench.OPPONENTS["reference"]()], hand_cap=60)))
        return out[0], seeds.get(id(hero))
    (r1, s1), (r2, s2) = go(), go()
    return r1 == r2 and bool(s1) and s1 == s2


def same_name_salt():
    a, b = bench.PokerCpp(sims=SIMS), bench.PokerCpp(sims=SIMS)
    s = record(lambda: bench.play_hand(5, [a, b]))
    return bool(s.get(id(a))) and bool(s.get(id(b))) and s[id(a)][0] != s[id(b)][0]


def seat_order():
    # same agent, same deal, seats swapped: the seeds must differ.
    # Some deals end before the hero decides in one seat, so scan a few deals.
    ref = bench.OPPONENTS["reference"]
    compared = 0
    for d in range(1, 11):
        a1 = bench.PokerCpp(sims=SIMS)
        s1 = record(lambda: bench.play_hand(d, [a1, ref()])).get(id(a1))
        a2 = bench.PokerCpp(sims=SIMS)
        s2 = record(lambda: bench.play_hand(d, [ref(), a2])).get(id(a2))
        if s1 and s2:
            compared += 1
            if s1 == s2:
                return False
    return compared > 0


def names_differ():
    st = bench.OPPONENTS["station"]
    compared = 0
    for d in range(1, 11):
        a = bench.PokerCpp(sims=SIMS, name="alpha")
        sa = record(lambda: bench.play_hand(d, [a, st()])).get(id(a))
        b = bench.PokerCpp(sims=SIMS, name="beta")
        sb = record(lambda: bench.play_hand(d, [b, st()])).get(id(b))
        if sa and sb:
            compared += 1
            if sa == sb:
                return False
    return compared > 0


def aa_duplicate():
    # H and V share a name; H's seat-0 seeds (play 1) must differ from V's
    # seat-0 seeds (play 2, swapped).
    compared = 0
    for d in range(1, 11):
        h, v = bench.PokerCpp(sims=SIMS), bench.PokerCpp(sims=SIMS)
        log, plays = [], [0]
        orig_dec, orig_play = bench.pokercpp_engine.decide, bench.play_hand

        def dec(*a, **kw):
            who = sys._getframe(1).f_locals.get("self")
            log.append((plays[0], id(who), kw["seed"]))
            return orig_dec(*a, **kw)

        def play(*a, **kw):
            plays[0] += 1
            return orig_play(*a, **kw)

        bench.pokercpp_engine.decide, bench.play_hand = dec, play
        try:
            bench.duplicate_match(2, h, v, seed0=d)
        finally:
            bench.pokercpp_engine.decide, bench.play_hand = orig_dec, orig_play
        sh = [s for p, i, s in log if p == 1 and i == id(h)]
        sv = [s for p, i, s in log if p == 2 and i == id(v)]
        if sh and sv:
            compared += 1
            if sh == sv:
                return False
    return compared > 0


case("1a insert one hand (reference)", inserted_hand("reference"))
case("1b insert one hand (station)", inserted_hand("station"))
case("2 run to run, memory on", run_to_run)
case("3 match mode repeat", match_mode)
case("4 same-name salt", same_name_salt)
case("5 seat order changes seed", seat_order)
case("6 different names, same seat", names_differ)
case("7 A/A duplicate play", aa_duplicate)
sys.exit(1 if fails else 0)
