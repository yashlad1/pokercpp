"""Black-box check: relabelling the suits leaves the engine's decision unchanged (#68).

Run:  python3 chipzen/test_suit_relabel.py [MODULE_DIR]

Tolerance, stated up front. equity is a Monte Carlo mean over SIMS = 20000 runouts,
so its standard error is at most sqrt(0.25 / 20000) = 0.0035. A relabelled spot
draws different cards from the same seed, so the two estimates are independent
and their difference has standard error at most sqrt(2) * 0.0035 = 0.0050.
TOL = 0.02 is four of those (4 * 0.0050 = 0.0200). A correct engine
passes one comparison with probability above 0.99993, so over the ~100
comparisons here, with fixed seeds, a failure by chance is under 1%. A
suit-dependent bug (a flush or a blocker counted for one suit only) moves
equity by several points, above TOL, and the draw-heavy spots are built so it would.

Action check: it is made only where the original's realized equity is at least
2 * TOL = 0.04 away from the price to call (`required`). There noise cannot cross
the call/fold line. Spots without a bet to call have required 0 and are
compared on equity only. Spots nearer the margin are still checked on equity.
Checked-to actions may differ under relabelling: the bluff draw hashes the exact cards, suits included, so check (b) runs only where there is a price to call.
Check (b) was seen failing with the relabelled action doctored to a different one: AssertionError "pre-AKs-open seed 11 swap-all: action call vs fold".
Identity relabelling must give the identical dict (same seed, same cards).
"""

import sys

MODULE_DIR = sys.argv[1] if len(sys.argv) > 1 else "chipzen"
sys.path.insert(0, MODULE_DIR)

import pokercpp_engine

SIMS = 20000
TOL = 0.02
SEEDS = (11, 22, 33)

# Spot: (hole, board, pot, to_call). Stack 9000, bb 100, min raise 2x the call.
SPOTS = {
    "pre-AKs-open":   (["Ah", "Kh"], [], 300, 200),
    "pre-76s-free":   (["7s", "6s"], [], 150, 0),
    "pre-QJo-open":   (["Qh", "Jd"], [], 300, 200),
    "flop-flushdraw": (["Ah", "5h"], ["Kh", "9h", "2c"], 400, 200),
    "flop-top-pair":  (["Ks", "Qd"], ["Kc", "7d", "2h"], 300, 0),
    "flop-air-bet":   (["Js", "Tc"], ["Ah", "8d", "3c"], 600, 600),
    "turn-flush-bet": (["Qs", "Js"], ["As", "9s", "4d", "2c"], 800, 400),
    "turn-set-free":  (["8c", "8d"], ["8h", "Ks", "3d", "2c"], 600, 0),
    "river-flush":    (["Ad", "3d"], ["Kd", "9d", "5d", "2c", "Js"], 1000, 500),
    "river-nothing":  (["Ac", "Qd"], ["Kh", "9h", "5h", "2h", "Js"], 1000, 800),
}

# Fixed suit permutations, applied to hole and board alike.
PERMS = {
    "identity":   {"c": "c", "d": "d", "h": "h", "s": "s"},
    "swap-all":   {"c": "d", "d": "c", "h": "s", "s": "h"},
    "cycle":      {"c": "d", "d": "h", "h": "s", "s": "c"},
    "swap-hs":    {"c": "c", "d": "d", "h": "s", "s": "h"},
    "reverse":    {"c": "s", "d": "h", "h": "d", "s": "c"},
}


def relabel(cards, perm):
    return [c[0] + perm[c[1]] for c in cards]


def run(spot, perm, seed, hole_perm=None):
    hole, board, pot, to_call = spot
    hole = relabel(hole, hole_perm or perm)
    board = relabel(board, perm)
    return pokercpp_engine.decide(hole, board, pot, to_call, max(2 * to_call, 200),
                                  9000, 9000, 100, sims=SIMS, villain_raises=1, seed=seed)


def check(orig, rel, label):
    """(a) equity within TOL; (b) same action when realized is >= 2*TOL from the price."""
    d = abs(rel["equity"] - orig["equity"])
    assert d <= TOL, f"{label}: equity {orig['equity']:.4f} vs {rel['equity']:.4f}, diff {d:.4f} > {TOL}"
    if orig["required"] > 0 and abs(orig["realized"] - orig["required"]) >= 2 * TOL:
        assert rel["action"] == orig["action"], f"{label}: action {orig['action']} vs {rel['action']}"


def test_identity_is_exact():
    for name, spot in SPOTS.items():
        for seed in SEEDS:
            assert run(spot, PERMS["identity"], seed) == run(spot, PERMS["identity"], seed), name


def test_relabel_keeps_decision():
    checked_action = 0
    for name, spot in SPOTS.items():
        for seed in SEEDS:
            orig = run(spot, PERMS["identity"], seed)
            if orig["required"] > 0 and abs(orig["realized"] - orig["required"]) >= 2 * TOL:
                checked_action += 1
            for pname, perm in PERMS.items():
                if pname != "identity":
                    check(orig, run(spot, perm, seed), f"{name} seed {seed} {pname}")
    assert checked_action >= 10, checked_action  # the action check must actually run


if __name__ == "__main__":
    test_identity_is_exact()
    test_relabel_keeps_decision()
    print("suit relabel tests: all passed")
