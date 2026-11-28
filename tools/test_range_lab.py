#!/usr/bin/env python3
"""Black-box tests for tools/range_lab.py (#37, step 1: offline measurement, ships nothing).

Written from the design comment on #37 only. Names and signatures the spec does not fix are
FIXED HERE, so the implementer must match them:

  Cards are two-character strings ("Ah", "Td"). A combo is a STRING of its two cards in DECK
  order: ranks "23456789TJQKA" ascending, then suits "cdhs"; so Ah+6s is "6sAh". The tests build
  keys with key(a, b) below. Every weight / strength dict is keyed that way.

  hard_range(frac, dead=())          -> set of combo keys: the top `frac` of the 1,326 combos in
                                        montecarlo/preflop_ranks.h order (class granularity, as the
                                        engine does), THEN minus any combo holding a dead card.
  prior_weights(dead=())             -> {combo: w > 0} over all live combos (no card in `dead`):
                                        the same ranking, softened (higher rank, higher weight).
  strength_pct(board, dead=())       -> {combo: s in [0, 1]} over combos holding no card of
                                        `dead` or `board`; 1 = best. Percentile among those
                                        combos on this board (pokerkit StandardHighHand); with an
                                        empty board, the preflop rank percentile.
  p_action(action, s, raise_cut, fold_cut, k=12.0, eps=0.05) -> float, action in
                                        {"raise", "call", "fold"}; raise_cut = 1 - raise_rate,
                                        fold_cut = fold_rate.
  update(w, action, s, raise_rate, fold_rate, alpha=0.05) -> a NEW dict w2 over the keys of w:
                                        w2[c] = w[c] * p_action(action, s[c], 1-raise_rate,
                                        fold_rate), then the floor (1-alpha)*w2 + alpha*mean(w2).
                                        The input dict is not relied on to stay unmodified.
  in_top_mass(w, shown, mass)        -> bool, as in the design sketch.
  log_score(w, shown)                -> log(w[shown] * len(w) / sum(w.values())).
  CLI: range_lab.py LOG [LOG ...] [--out FILE.json] prints a table (one line per street, named
       preflop / flop / turn / river) and writes JSON
       {"streets": {"<street>": {"n": int, "covered_hard_pct": float 0-100,
                                 "covered_weighted_pct": float 0-100, "mean_log_score": float}}}.
       One decision of ours = one row; street field 0/3/4/5 = preflop/flop/turn/river.
       Dead cards for a decision: our hole + the board cards shown on that street.
"""
import itertools
import json
import math
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "range_lab.py"
sys.path.insert(0, str(HERE))

DECK = [r + s for r in "23456789TJQKA" for s in "cdhs"]


def key(a, b):
    a, b = sorted((a, b), key=DECK.index)
    return a + b


def lab():
    import range_lab
    return range_lab


def uniform(cards_out):
    live = [c for c in DECK if c not in cards_out]
    return {key(a, b): 1.0 for a, b in itertools.combinations(live, 2)}


# ---- today's range ---------------------------------------------------------------------

def test_hard_range_top_and_bottom():
    rl = lab()
    top = rl.hard_range(0.01, ())
    assert {key("A" + a, "A" + b) for a, b in itertools.combinations("cdhs", 2)} <= top  # AA
    assert {key("K" + a, "K" + b) for a, b in itertools.combinations("cdhs", 2)} <= top  # KK
    half = rl.hard_range(0.5, ())
    o72 = {key("7" + a, "2" + b) for a in "cdhs" for b in "cdhs" if a != b}
    assert len(o72) == 12 and not (o72 & half)
    assert len(rl.hard_range(1.0, ())) == 1326


def test_hard_range_removes_dead_cards():
    rl = lab()
    r = rl.hard_range(1.0, {"As", "Kd"})
    assert len(r) == 50 * 49 // 2
    assert all("As" not in (c[:2], c[2:]) and "Kd" not in (c[:2], c[2:]) for c in r)


def test_prior_weights_follow_the_ranking():
    rl = lab()
    w = rl.prior_weights(())
    assert len(w) == 1326 and all(v > 0 for v in w.values())
    assert w[key("Ac", "Ad")] > w[key("7c", "2d")]
    assert w[key("Kc", "Kd")] > w[key("7c", "2d")]
    assert len(rl.prior_weights({"As"})) == 51 * 50 // 2


# ---- strength percentile ---------------------------------------------------------------

BOARD = ["6d", "9s", "3d", "6c", "5c"]
OURS = {"Kh", "Jd"}


def test_strength_pct_covers_live_combos_in_unit_interval():
    s = lab().strength_pct(BOARD, OURS)
    assert len(s) == 45 * 44 // 2
    assert all(0.0 <= v <= 1.0 for v in s.values())
    assert max(s.values()) > 0.99 and min(s.values()) < 0.01


def test_strength_pct_orders_hands_on_the_board():
    s = lab().strength_pct(BOARD, OURS)
    boat = s[key("9h", "9d")]        # full house
    a6 = s[key("6s", "Ah")]          # trips, ace kicker
    air = s[key("Qh", "Ts")]         # high card only
    assert boat > a6 > air


def test_strength_pct_preflop_uses_the_ranking():
    s = lab().strength_pct([], ())
    assert len(s) == 1326
    assert s[key("Ac", "Ad")] > 0.95 > 0.2 > s[key("7c", "2d")]


# ---- p_action --------------------------------------------------------------------------

GRID = [i / 100 for i in range(101)]


def test_p_action_monotone_in_strength():
    p = lab().p_action
    for rr, fr in [(0.15, 0.30), (0.4, 0.1), (0.05, 0.5)]:
        raise_ = [p("raise", s, 1 - rr, fr) for s in GRID]
        fold = [p("fold", s, 1 - rr, fr) for s in GRID]
        assert all(b >= a - 1e-12 for a, b in zip(raise_, raise_[1:])), "raise rises with s"
        assert all(b <= a + 1e-12 for a, b in zip(fold, fold[1:])), "fold falls with s"
        assert raise_[-1] > raise_[0] + 0.3 and fold[0] > fold[-1] + 0.3


def test_p_action_every_action_at_least_eps():
    p = lab().p_action
    for rr, fr in [(0.15, 0.30), (0.4, 0.1), (0.0, 0.0), (1.0, 1.0)]:
        for s in GRID:
            for a in ("raise", "call", "fold"):
                v = p(a, s, 1 - rr, fr)
                assert 0.05 - 1e-9 <= v <= 1.0 + 1e-9, (a, s, rr, fr, v)


def test_p_action_cutoffs_follow_the_stated_rates():
    p = lab().p_action
    mean = lambda a, rr, fr: sum(p(a, s, 1 - rr, fr) for s in GRID) / len(GRID)
    for rr in (0.1, 0.3, 0.6):  # over uniform strength the raise share is about the rate
        assert abs(mean("raise", rr, 0.2) - rr) < 0.1, rr
    for fr in (0.1, 0.3, 0.5):
        assert abs(mean("fold", 0.1, fr) - fr) < 0.1, fr
    assert mean("raise", 0.6, 0.2) > mean("raise", 0.1, 0.2) + 0.3
    assert mean("fold", 0.1, 0.5) > mean("fold", 0.1, 0.1) + 0.2
    # a 15% raiser raises the very top, not the middle
    assert p("raise", 0.97, 0.85, 0.2) > 3 * p("raise", 0.5, 0.85, 0.2)


# ---- update ----------------------------------------------------------------------------

FLOP = ["Ks", "8d", "3c"]


def wmean(w, s):
    t = sum(w.values())
    return sum(w[c] * s[c] for c in w) / t


def test_update_raise_moves_weight_to_strong_combos():
    rl = lab()
    s = rl.strength_pct(FLOP, OURS)
    w0 = {c: 1.0 for c in s}
    w1 = rl.update(dict(w0), "raise", s, 0.2, 0.2)
    assert wmean(w1, s) > wmean(w0, s) + 0.1
    strong = [c for c in s if s[c] > 0.9]
    weak = [c for c in s if s[c] < 0.3]
    assert min(w1[c] for c in strong) > max(w1[c] for c in weak)
    w2 = rl.update(dict(w0), "fold", s, 0.2, 0.2)  # a fold does the opposite
    assert wmean(w2, s) < wmean(w0, s) - 0.1


def test_update_never_zeroes_a_weight_and_keeps_the_floor():
    rl = lab()
    s = rl.strength_pct(FLOP, OURS)
    w = {c: 1.0 for c in s}
    for act in ["raise", "raise", "raise", "raise", "raise", "raise", "fold", "call"]:
        w = rl.update(dict(w), act, s, 0.15, 0.3)
        mean = sum(w.values()) / len(w)
        assert min(w.values()) > 0.0
        assert min(w.values()) >= 0.05 * mean - 1e-12, "floor alpha=0.05 of the mean weight"
    assert set(w) == set(s)


# ---- the board case --------------------------------------------------------------------

def test_board_case_river_shove_keeps_a6_offsuit():
    rl = lab()
    dead = set(BOARD) | OURS
    a6 = key("6s", "Ah")  # A6 offsuit: trips on 6d 9s 3d 6c 5c
    w = rl.prior_weights(dead)
    for n in (3, 4, 5):   # bet flop, bet turn, shove river
        s = rl.strength_pct(BOARD[:n], dead)
        w = rl.update(dict(w), "raise", s, 0.35, 0.3)
    mean = sum(w.values()) / len(w)
    assert w[a6] > 2 * mean, "A6o weight far above the average combo"
    assert rl.in_top_mass(w, a6, 0.5)
    # today's hard range at 0.06 gave it nothing
    a6_all = {key("6" + a, "A" + b) for a in "hs" for b in "cdhs" if "A" + b not in dead}
    assert a6_all and not (a6_all & rl.hard_range(0.06, dead))


# ---- in_top_mass / log_score -----------------------------------------------------------

def test_in_top_mass():
    f = lab().in_top_mass
    w = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert f(w, "a", 0.4) and not f(w, "b", 0.4) and not f(w, "c", 0.4)
    assert f(w, "b", 0.8) and not f(w, "c", 0.8)
    assert f(w, "c", 0.9)
    assert f({k: v * 7 for k, v in w.items()}, "b", 0.8), "scale-free"


def test_log_score():
    f = lab().log_score
    assert abs(f({"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}, "b")) < 1e-12
    w = {"a": 6.0, "b": 1.0, "c": 1.0, "d": 0.0001}
    assert abs(f(w, "a") - math.log(6.0 * 4 / sum(w.values()))) < 1e-9
    assert f(w, "a") > 0 > f(w, "d")


# ---- the coverage tool (CLI) -----------------------------------------------------------
# Blinds 50/100; client_pos 0 = we are the big blind, 1 = small blind. Slumbot's hole is bot_hole.

def dec(street, sent, rng):
    act = {"c": "call", "f": "fold", "k": "check"}.get(sent, "raise")
    return {"street": street, "pot": 300, "to_call": 0, "sent": sent, "action": act,
            "amount": 0, "equity": 0.5, "range": rng, "bluff": False}


def hand(action, pos, hole, bot, board, decs):
    return {"action": action, "client_pos": pos, "hole": hole, "bot_hole": bot, "board": board,
            "decisions": decs, "winnings": 0, "expected": 0, "showdown": False}


HANDS = [
    # H1: Slumbot AhAd, range 0.10 on preflop + flop (check, fold). AA is top 10%: 3 covered.
    hand("b200c/kb100f", 0, ["7c", "2d"], ["Ah", "Ad"], ["Kc", "8s", "3h"],
         [dec(0, "c", 0.10), dec(3, "k", 0.10), dec(3, "f", 0.10)]),
    # H2: Slumbot 7h2s (72o), range 0.45 preflop. 72o is not in the top 45%: miss.
    hand("b250f", 1, ["Ac", "Kd"], ["7h", "2s"], [], [dec(0, "b250", 0.45)]),
    # H3: Slumbot QhJh (QJs), range 0.45 on all four streets: 4 covered.
    hand("b200c/kk/kk/kk", 0, ["9c", "2c"], ["Qh", "Jh"], ["Td", "4s", "3d", "8c", "Ks"],
         [dec(0, "c", 0.45), dec(3, "k", 0.45), dec(4, "k", 0.45), dec(5, "k", 0.45)]),
    # H4: Slumbot 8d3c (83o). Preflop range 1.0: covered. Flop/turn/river range 0.30: 3 misses.
    hand("b250c/kk/kk/kk", 1, ["Ad", "Kc"], ["8d", "3c"], ["9s", "5h", "2d", "Jc", "6h"],
         [dec(0, "b250", 1.0), dec(3, "k", 0.30), dec(4, "k", 0.30), dec(5, "k", 0.30)]),
]
# by hand: preflop n=4 hard 3/4=75%; flop n=4 (H1 x2, H3, H4) hard 3/4=75%;
#          turn n=2 (H3, H4) hard 1/2=50%; river n=2 (H3, H4) hard 1/2=50%.
EXPECT = {"preflop": (4, 75.0), "flop": (4, 75.0), "turn": (2, 50.0), "river": (2, 50.0)}


def run_cli(d, out_name):
    log = pathlib.Path(d) / "s.jsonl"
    log.write_text("".join(json.dumps(h) + "\n" for h in HANDS))
    out = pathlib.Path(d) / out_name
    r = subprocess.run([sys.executable, str(TOOL), str(log), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, out.read_text()


def test_cli_hard_coverage_matches_hand_count():
    with tempfile.TemporaryDirectory() as d:
        stdout, js = run_cli(d, "o.json")
    streets = json.loads(js)["streets"]
    for name, (n, hard) in EXPECT.items():
        row = streets[name]
        assert row["n"] == n, name
        assert abs(row["covered_hard_pct"] - hard) < 1e-6, name
        assert 0.0 <= row["covered_weighted_pct"] <= 100.0, name
        assert math.isfinite(row["mean_log_score"]), name
        assert name in stdout
    assert "turn" in stdout and "river" in stdout and "flop" in stdout


def test_cli_two_runs_are_identical():
    with tempfile.TemporaryDirectory() as d:
        a = run_cli(d, "a.json")
        b = run_cli(d, "b.json")
    assert a == b
