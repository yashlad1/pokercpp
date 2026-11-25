# Black-box tests for the in-match bluff detector, written from the spec only.
# Run from chipzen/:  python test_bluff.py
import os, sys, json, logging, importlib.util, subprocess
os.environ["POKERCPP_SIMS"] = "2000"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import opponent as new_mod

def _load_head():
    src = subprocess.check_output(["git", "-C", HERE, "show", "HEAD:chipzen/opponent.py"])
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "opponent_head.py")
    open(p, "wb").write(src)
    sp = importlib.util.spec_from_file_location("opponent_head", p)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m
head_mod = _load_head()

fails = []
def report(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " :: " + str(detail)))
    if not ok:
        fails.append(name)

def safe(name, fn):
    try:
        fn()
    except Exception:
        import traceback
        report(name, False, "exception " + traceback.format_exc(limit=2).replace("\n", " | "))

def close(a, b, tol=1e-3):
    return abs(a - b) <= tol

# ---- expected values from the spec formulas
STEP = {1: 0.45, 2: 0.18, 3: 0.08}
def expected_bluff_floor(n, k, v):
    b = (k + 0.25 * 6.0) / (n + 6.0)
    w = min(1.0, n / 10.0)
    b_eff = 0.25 + w * (b - 0.25)
    scale = min(2.0, 0.75 / (1 - b_eff)) if (n >= 3 and b > 0.25) else 1.0
    return min(1.0, STEP[min(v, 3)] * scale) if scale > 1 else 0.0

# ---- result builders (live format); we are seat 0, opponent seat 1
ME, OPP = 0, 1
AIR_HC = (["As", "7h"], "High Card", ["As", "Kh", "9c", "7h", "4d"])
AIR_BOARD_PAIR = (["As", "7h"], "Pair", ["9h", "9c", "As", "Kh", "7h"])
PAIR_HOLE = (["As", "7h"], "Pair", ["7h", "7c", "As", "Kh", "9c"])
TWO_PAIR = (["As", "7h"], "Two Pair", ["As", "Ac", "7h", "7c", "9c"])
_hn = [0]
def result(hand=AIR_HC, opp_phases=("flop",), opp_seat=OPP, my_seat=ME, showdown=True, extra_hist=()):
    _hn[0] += 1
    hist = [{"seat": my_seat, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
            {"seat": opp_seat, "action": "post_big_blind", "amount": 100, "phase": "preflop"}]
    hist += [{"seat": opp_seat, "action": "raise", "amount": 400, "phase": ph} for ph in opp_phases]
    hist += list(extra_hist)
    sd = []
    if showdown:
        sd = [{"seat": my_seat, "hole_cards": ["Kd", "Qs"], "hand_rank": "Pair", "best_hand": ["Kd", "Kh", "9c", "7s", "4d"]},
              {"seat": opp_seat, "hole_cards": hand[0], "hand_rank": hand[1], "best_hand": hand[2]}]
    return {"hand_number": _hn[0], "winner_seats": [opp_seat], "pot": 1200,
            "payouts": [{"seat": opp_seat, "amount": 1200}], "showdown": sd,
            "action_history": hist, "stacks": [9400, 10600]}

def feed(opp, n_air, n_non_air=0):
    for _ in range(n_air):
        opp.learn(result(AIR_HC), ME)
    for _ in range(n_non_air):
        opp.learn(result(TWO_PAIR), ME)
    return opp

def floors(opp, vs=(0, 1, 2, 3, 5)):
    return [opp.range_floor(v) for v in vs]

def head_opp(sawseq=()):
    h = head_mod.Opponent()
    for hand, vr in sawseq: h.saw(hand, vr)
    return h

# ---- tests
def t_fresh_matches_head():
    seq = [(i, (i % 4)) for i in range(40)]
    a, h = new_mod.Opponent(), head_opp()
    for hand, vr in seq:
        a.saw(hand, vr); h.saw(hand, vr)
    got, want = floors(a, range(0, 5)), floors(h, range(0, 5))
    report("fresh Opponent range_floor equals HEAD for v=0..4", got == want, (got, want))

def t_gate_two_air():
    a = new_mod.Opponent(); feed(a, 2)
    h = head_opp()
    report("2 shown air bets change nothing (gate)", floors(a) == floors(h), (floors(a), floors(h)))

def t_never_narrow():
    a = new_mod.Opponent(); feed(a, 0, 10)
    h = head_opp()
    report("10 shown non-air bets change nothing (never narrows)", floors(a) == floors(h), (floors(a), floors(h)))

def t_example_4_3():
    a = new_mod.Opponent(); feed(a, 3, 1)
    want = max(head_opp().range_floor(2), 0.2015)
    got = a.range_floor(2)
    report("n=4,k=3 gives bluff_floor(2)=0.2015", close(got, want) and close(expected_bluff_floor(4, 3, 2), 0.2015), (got, want))

def t_example_10_10():
    a = new_mod.Opponent(); feed(a, 10)
    h = head_opp()
    for v, want in [(1, 0.90), (2, 0.36), (3, 0.16), (5, 0.16)]:
        want = max(h.range_floor(v), want)
        got = a.range_floor(v)
        report("n=10,k=10 range_floor(%d)=%.2f" % (v, want), close(got, want), got)
    report("range_floor(0) stays 0.0 after 10 air", a.range_floor(0) == 0.0, a.range_floor(0))

def t_max_with_old():
    seq = [(i, 3) for i in range(60)]
    a, h = new_mod.Opponent(), head_opp(seq)
    for hand, vr in seq: a.saw(hand, vr)
    old = [h.range_floor(v) for v in (1, 2, 3)]
    feed(a, 4, 0)  # n=4,k=4 widening is small
    got = [a.range_floor(v) for v in (1, 2, 3)]
    want = [max(o, expected_bluff_floor(4, 4, v)) for o, v in zip(old, (1, 2, 3))]
    report("range_floor is max(old floor, bluff floor)", all(close(g, w, 1e-9) for g, w in zip(got, want)) and max(old) > 0.5, (got, want, old))

def base3():
    a = new_mod.Opponent(); feed(a, 3)  # n=3,k=3 -> floor(1)=0.5 (own computation)
    return a
def t_base_sanity():
    a = base3()
    report("n=3,k=3 gives range_floor(1)>=0.5 (own calc 0.5000)", close(a.range_floor(1), max(head_opp().range_floor(1), 0.5)), a.range_floor(1))

def unchanged_after(name, res):
    a = base3(); before = floors(a)
    a.learn(res, ME)
    report(name, floors(a) == before, (floors(a), before))

def t_counts():
    unchanged_after("preflop-only opponent raise at showdown does not count", result(AIR_HC, opp_phases=("preflop",)))
    unchanged_after("hand with no showdown does not count", result(AIR_HC, showdown=False))
    unchanged_after("our own postflop raise does not count",
                    result(AIR_HC, opp_phases=(), extra_hist=[{"seat": ME, "action": "raise", "amount": 400, "phase": "flop"}]))
    a = new_mod.Opponent(); feed(a, 2)
    a.learn(result(AIR_HC, opp_phases=("flop", "turn", "river")), ME)
    want = max(head_opp().range_floor(1), expected_bluff_floor(3, 3, 1))
    report("hand with several opponent postflop raises counts once", close(a.range_floor(1), want), (a.range_floor(1), want))
    # opponent as seat 0, us as seat 1: seat taken from my_seat argument
    a = new_mod.Opponent()
    for _ in range(3): a.learn(result(AIR_HC, opp_seat=0, my_seat=1), 1)
    report("my_seat=1 works (opponent is seat 0)", close(a.range_floor(1), max(head_opp().range_floor(1), 0.5)), a.range_floor(1))

def widened_if(name, hand, expect_widen):
    a = new_mod.Opponent()
    for _ in range(3): a.learn(result(hand), ME)
    h = head_opp()
    if expect_widen:
        ok = close(a.range_floor(1), max(h.range_floor(1), 0.5))
    else:
        ok = a.range_floor(1) == h.range_floor(1)
    report(name, ok, (a.range_floor(1), h.range_floor(1)))

def t_air():
    widened_if("High Card is air", AIR_HC, True)
    widened_if("Pair with paired rank on the board only is air", AIR_BOARD_PAIR, True)
    widened_if("Pair using a hole card is not air", PAIR_HOLE, False)
    widened_if("Two Pair is not air", TWO_PAIR, False)

def t_bad_seat():
    a = base3()
    for seat in (None, "x", 99):
        a.learn(result(AIR_HC), seat)
    report("learn with bad my_seat does not raise", True)

def t_garbage_no_change():
    a = base3(); before = floors(a)
    for g in [None, {}, {"showdown": None}, {"showdown": "x", "action_history": 5}, 7, "abc",
              {"showdown": [{"seat": 1}], "action_history": [{"seat": 1, "action": "raise", "phase": "flop"}]}]:
        a.learn(g, ME)
    report("garbage learn() inputs change nothing", floors(a) == before, (floors(a), before))

def t_bot_log():
    import bot as botmod
    recs = []
    class H(logging.Handler):
        def emit(self, r): recs.append(r.getMessage())
    root = logging.getLogger(); root.setLevel(logging.DEBUG); root.addHandler(H())
    b = botmod.PokerCppBot()
    b.on_match_start({"seats": [{"seat": 0, "is_self": False}, {"seat": 1, "is_self": True}]})
    for _ in range(3):
        b.on_round_result({"type": "round_result", "result": result(AIR_HC, opp_seat=0, my_seat=1)})
    lines = [m for m in recs if m.startswith("BLUFF ")]
    want = "BLUFF n=3 k=3 b=0.500 scale=1.111"
    report("BLUFF log line on n change, seat from is_self", want in lines, lines)
    report("BLUFF logged once per n change", len([m for m in lines if m.startswith("BLUFF n=3 ")]) == 1, lines)
    n0 = len(lines)
    b.on_round_result({"type": "round_result", "result": result(AIR_HC, opp_phases=("preflop",), opp_seat=0, my_seat=1)})
    report("no BLUFF line when n does not change", len([m for m in recs if m.startswith("BLUFF ")]) == n0)

for nm, f in [("fresh", t_fresh_matches_head), ("gate", t_gate_two_air), ("narrow", t_never_narrow),
              ("ex43", t_example_4_3), ("ex1010", t_example_10_10), ("max", t_max_with_old),
              ("base", t_base_sanity), ("counts", t_counts), ("air", t_air),
              ("garbage", t_garbage_no_change), ("badseat", t_bad_seat), ("botlog", t_bot_log)]:
    safe(nm, f)

if fails:
    print("bluff tests FAILED:", fails); sys.exit(1)
print("bluff tests: all passed")
