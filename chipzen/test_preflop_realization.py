"""Black-box self-check for the preflop_realization option of pokercpp_engine.

Run:  python3 chipzen/test_preflop_realization.py [MODULE_DIR]

MODULE_DIR defaults to "chipzen" and is put on sys.path before the import.
"""

import sys

MODULE_DIR = sys.argv[1] if len(sys.argv) > 1 else "chipzen"
sys.path.insert(0, MODULE_DIR)

import pokercpp_engine

SEED = 4242


def decide(spot, **kw):
    return pokercpp_engine.decide(
        spot["hole"], spot["board"], spot["pot"], spot["to_call"],
        spot["min_raise"], spot["max_raise"], spot["stack"], spot["bb"],
        sims=2000, villain_raises=1, seed=SEED, **kw,
    )


PREFLOP = dict(hole=["Qh", "Jd"], board=[], pot=300, to_call=200,
               min_raise=400, max_raise=9000, stack=9000, bb=100)

FLOP = dict(hole=["Qh", "Jd"], board=["Ks", "7c", "2d"], pot=200,
            to_call=100, min_raise=200, max_raise=9000, stack=9000, bb=100)

# 15 bb effective, facing an open. TT folds at realization 0.75 and not at 0.95 (found by scanning all 169 hands).
SHORT = dict(hole=["Th", "Td"], board=[], pot=150, to_call=200,
             min_raise=400, max_raise=1500, stack=1500, bb=100)


def test_default_is_085():
    for spot in (PREFLOP, FLOP):
        assert decide(spot) == decide(spot, preflop_realization=0.85), spot


def test_preflop_ratio():
    a = decide(PREFLOP, preflop_realization=0.95)
    assert abs(a["realized"] / a["equity"] - 0.95) < 1e-9, a
    d = decide(PREFLOP)
    assert abs(d["realized"] / d["equity"] - 0.85) < 1e-9, d


def test_flop_ignores_it():
    a = decide(FLOP, preflop_realization=0.75)
    b = decide(FLOP, preflop_realization=0.95)
    assert a == b, (a, b)
    assert abs(a["realized"] / a["equity"] - 0.82) < 1e-9, a


def test_short_stack_fold_flips():
    lo = decide(SHORT, preflop_realization=0.75)
    hi = decide(SHORT, preflop_realization=0.95)
    assert lo["action"] == "fold", lo
    assert hi["action"] != "fold", hi


if __name__ == "__main__":
    test_default_is_085()
    test_preflop_ratio()
    test_flop_ignores_it()
    test_short_stack_fold_flips()
    print("preflop realization tests: all passed")
