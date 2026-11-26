"""Black-box self-check for the seed option of the pokercpp_engine module.

Run:  python3 chipzen/test_engine_seed.py [MODULE_DIR]

MODULE_DIR defaults to "chipzen" and is put on sys.path before the import.
"""

import sys

MODULE_DIR = sys.argv[1] if len(sys.argv) > 1 else "chipzen"
sys.path.insert(0, MODULE_DIR)

import pokercpp_engine


def decide(hole, board, pot, to_call, min_raise, max_raise, stack, bb,
           villain_raises, seed):
    return pokercpp_engine.decide(
        hole, board, pot, to_call, min_raise, max_raise, stack, bb,
        sims=2000, villain_raises=villain_raises, seed=seed,
    )


FLOP = dict(hole=["Qh", "Jd"], board=["Ks", "7c", "2d"], pot=200,
            to_call=100, min_raise=200, max_raise=9000, stack=9000,
            bb=100, villain_raises=1)

RIVER = dict(hole=["7h", "2c"], board=["As", "Kd", "Qc", "9h", "4s"],
             pot=300, to_call=0, min_raise=100, max_raise=9000,
             stack=9000, bb=100, villain_raises=1)


def same_result(a, b):
    return (a["equity"] == b["equity"] and a["action"] == b["action"]
            and a["amount"] == b["amount"])


def test_same_seed_repeats():
    a = decide(seed=12345, **FLOP)
    b = decide(seed=12345, **FLOP)
    assert same_result(a, b), f"seed=12345 gave {a} then {b}"


def test_different_seeds_differ():
    a = decide(seed=12345, **FLOP)
    b = decide(seed=67890, **FLOP)
    assert a["equity"] != b["equity"], \
        f"seeds 12345 and 67890 both gave equity {a['equity']}"


def test_seed_zero_is_fresh():
    equities = {decide(seed=0, **FLOP)["equity"] for _ in range(5)}
    assert len(equities) >= 2, f"seed=0 gave only {equities} over 5 calls"


def test_river_bluff_path_repeats():
    a = decide(seed=777, **RIVER)
    b = decide(seed=777, **RIVER)
    assert same_result(a, b), f"river seed=777 gave {a} then {b}"


if __name__ == "__main__":
    test_same_seed_repeats()
    test_different_seeds_differ()
    test_seed_zero_is_fresh()
    test_river_bluff_path_repeats()
    print("engine seed tests: all passed")
