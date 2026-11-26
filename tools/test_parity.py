"""Parity test: the engine hero and the bot.py hero must play identically.

Same seeds, faithful mode (full history, real hand numbers), against reference,
maniac, aggro and random: per-pair results and every (action, amount) decision must match
exactly. bench --hero bot minus --hero engine was +0.0 in the v4 release (G2).

Runs in both wire modes: "bench" (today's shape) and "live" (what the live server sends).
Run: PYTHONPATH=chipzen python tools/test_parity.py [--pairs 50] [--sims 200]
     BOT_PY=/path/to/bot_copy.py ... tests a patched copy of chipzen/bot.py.
     --pairs 1000 is the record run.
"""
import argparse
import importlib.util
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pairs", type=int, default=50, help="pairs per opponent (1000 = record run)")
ap.add_argument("--sims", type=int, default=200)
args = ap.parse_args()

if os.environ.get("BOT_PY"):  # Bot does `import bot`, so seat the copy in sys.modules first
    spec = importlib.util.spec_from_file_location("bot", os.environ["BOT_PY"])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot"] = mod
    spec.loader.exec_module(mod)

BB, STACK = 100, 100


def play(kind, opp, wire):
    bench.pokercpp_engine.decide = bench.REAL_DECIDE  # Bot() leaves its wrapper behind
    hero = (bench.Bot(BB // 2, BB, STACK * BB, args.sims, "full", "full", wire=wire)
            if kind == "bot" else bench.PokerCpp(sims=args.sims))
    log, act = [], hero.act

    def spy(v):
        r = act(v)
        log.append((v.hand, r))
        return r

    hero.act = spy
    res = bench.duplicate_match(args.pairs * 2, hero, bench.OPPONENTS[opp](),
                                blinds=(BB // 2, BB), stack=STACK * BB, seed0=1)
    bench.pokercpp_engine.decide = bench.REAL_DECIDE
    return res, log


fails = 0
for wire in ("bench", "live"):
    for opp in ("reference", "maniac", "aggro", "random"):
        t = time.time()
        try:
            (er, el), (br, bl) = play("engine", opp, wire), play("bot", opp, wire)
        except Exception as e:  # e.g. Bot has no wire keyword yet: count as a failure
            fails += 1
            print(f"FAIL: wire={wire}: {opp}: {type(e).__name__}: {e}")
            continue
        bad_pairs = sum(a != b for a, b in zip(er, br))
        bad_acts = sum(a != b for a, b in zip(el, bl)) + abs(len(el) - len(bl))
        ok = er == br and el == bl
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}: wire={wire}: {opp}: {len(er)} pairs, {len(el)} decisions, "
              f"{bad_pairs} pair mismatches, {bad_acts} action mismatches ({time.time() - t:.1f}s)")
sys.exit(1 if fails else 0)
