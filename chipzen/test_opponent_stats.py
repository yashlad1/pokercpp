"""Black-box tests for the per-match opponent stats foundation (#158, spec v2 + v2.1).

Written by the tester from the spec and the signatures only; no implementation body was read.
EVERY EXPECTED COUNT IN THE HAND-BUILT CASES WAS DERIVED BY HAND FROM THE SPEC. Neither the
47fcb67 Stats class, results/2026-11-26-live-scripts/opponent47.py nor the new code was run to
get an expectation. The live-log oracle (tests 'oracle_*') proves FIDELITY to the 24 Nov
numbers (which came from 47fcb67's own code), not correctness. Correctness rests on the
hand-built cases.

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_opponent_stats.py
(needs the built engine and pokerkit for the bench cases; see tools/build_engine.sh)

Readings of the spec that these tests commit to (also listed in the tester's report):
- first_in is recorded only when the opponent's first voluntary action is the first voluntary
  action of the hand (opponent is the small blind). vs_open / vs_shove follow the literal text:
  our first preflop action, then the opponent's next action.
- summary(): keys in the order first_in, vs_open, vs_shove (each @le10,@10to20,@deep,@na), cbet,
  checked_to, vs_bet@1..3. The tests accept keys with n=0 being present or absent; every key
  with n>0 must be there, exactly formatted, in that order.
- parse_actions' return shape is not specified, so it is tested only by length.
"""
import collections
import logging
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("POKERCPP_SIMS", "300")
from testutil import run

import opponent as opmod

SB, BB = 50, 100
EFF, DEPTH = 10000, 100.0      # 100 bb deep -> bucket "deep"


def H(seat, action, amount=0, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase}


# blind posts: seat 1 is the small blind (opponent when we are seat 0), seat 0 the big blind
P1 = [H(1, "post_small_blind", SB), H(0, "post_big_blind", BB)]
# seat 0 is the small blind (we open as seat 0)
P0 = [H(0, "post_small_blind", SB), H(1, "post_big_blind", BB)]


def obs(hist, our=0, eff=EFF, depth=DEPTH):
    st = opmod.OpponentStats()
    st.observe_hand(hist, our, eff, depth)
    return st


def nz(st):
    """The non-zero counts: {key: {outcome: n}}."""
    return {k: {o: n for o, n in v.items() if n} for k, v in st.counts.items()
            if any(v.values())}


def swap(hist):
    return [dict(e, seat=1 - e["seat"]) for e in hist]


def outs(key):
    d = opmod.OUTCOMES
    return list(d[key] if key in d else d[key.split("@")[0]])


# ---------- 1. hand-built histories ----------

def test_first_in_fold_limp_raise_shove_other():
    # opponent = seat 1 = SB; first voluntary action of the hand. Hand-derived:
    assert nz(obs(P1 + [H(1, "fold")])) == {"first_in@deep": {"fold": 1}}
    assert nz(obs(P1 + [H(1, "call", 50), H(0, "check")])) == {"first_in@deep": {"limp": 1}}
    assert nz(obs(P1 + [H(1, "raise", 250), H(0, "fold")])) == {"first_in@deep": {"raise": 1}}
    assert nz(obs(P1 + [H(1, "check")])) == {"first_in@deep": {"other": 1}}


def test_first_in_shove_by_amount_or_label():
    # shove(e): aggressive and (label all_in or amount >= eff)
    assert nz(obs(P1 + [H(1, "raise", 10000), H(0, "fold")])) == {"first_in@deep": {"shove": 1}}
    assert nz(obs(P1 + [H(1, "raise", 9999), H(0, "fold")])) == {"first_in@deep": {"raise": 1}}
    assert nz(obs(P1 + [H(1, "all_in", 3000), H(0, "fold")])) == {"first_in@deep": {"shove": 1}}
    # eff unknown: only the all_in label makes a shove, and the bucket is na
    st = obs(P1 + [H(1, "raise", 10000), H(0, "fold")], eff=None, depth=None)
    assert nz(st) == {"first_in@na": {"raise": 1}}
    st = obs(P1 + [H(1, "all_in", 10000), H(0, "fold")], eff=None, depth=None)
    assert nz(st) == {"first_in@na": {"shove": 1}}


def test_first_in_needs_opponent_small_blind():
    # we are the small blind (seat 1), the opponent (seat 0, big blind) acts second: no first_in
    assert nz(obs(P1 + [H(1, "call", 50), H(0, "check")], our=1)) == {}


def test_depth_buckets():
    h = P1 + [H(1, "call", 50), H(0, "check")]
    for depth, bucket in ((5, "le10"), (10, "le10"), (10.01, "10to20"), (20, "10to20"),
                          (20.01, "deep"), (100, "deep"), (None, "na")):
        st = obs(h, depth=depth, eff=None if depth is None else depth * BB)
        assert nz(st) == {f"first_in@{bucket}": {"limp": 1}}, (depth, nz(st))


def test_vs_open_every_outcome():
    o = [H(0, "raise", 250)]            # we open from the small blind
    cases = [
        ([H(1, "fold")], "fold"),
        ([H(1, "call", 150)], "call"),
        ([H(1, "raise", 750), H(0, "fold")], "raise"),
        ([H(1, "raise", 10000), H(0, "fold")], "shove"),
        ([H(1, "all_in", 9000), H(0, "fold")], "shove"),
        ([H(1, "check")], "other"),
    ]
    for tail, outcome in cases:
        assert nz(obs(P0 + o + tail)) == {"vs_open@deep": {outcome: 1}}, (tail, outcome)


def test_all_in_not_bigger_than_earlier_bet_is_a_call():
    o = P0 + [H(0, "raise", 250)]
    # amount <= the earlier same-street aggressive amount (either seat) -> a call, "no bigger"
    assert nz(obs(o + [H(1, "all_in", 150)])) == {"vs_open@deep": {"call": 1}}
    assert nz(obs(o + [H(1, "all_in", 250)])) == {"vs_open@deep": {"call": 1}}
    # one chip bigger is aggression, and the label makes it a shove
    assert nz(obs(o + [H(1, "all_in", 251), H(0, "fold")])) == {"vs_open@deep": {"shove": 1}}
    # postflop: the earlier street's larger bet does not count, only the same street
    h = P1 + [H(1, "call", 50), H(0, "check"),
              H(0, "bet", 100, "flop"), H(1, "call", 100, "flop"),
              H(0, "bet", 50, "turn"), H(1, "all_in", 60, "turn")]
    assert nz(obs(h))["vs_bet@2"] == {"raise": 1}
    # same street, equal amount -> call
    h = P1 + [H(1, "call", 50), H(0, "check"), H(0, "bet", 100, "flop"), H(1, "all_in", 100, "flop")]
    assert nz(obs(h))["vs_bet@1"] == {"call": 1}
    h = P1 + [H(1, "call", 50), H(0, "check"), H(0, "bet", 100, "flop"), H(1, "all_in", 101, "flop")]
    assert nz(obs(h))["vs_bet@1"] == {"raise": 1}


def test_vs_shove_every_outcome():
    for sh in (H(0, "raise", 10000), H(0, "all_in", 5000)):     # by amount, by label
        for tail, outcome in (([H(1, "fold")], "fold"), ([H(1, "call", 9900)], "call"),
                              ([H(1, "check")], "other")):
            assert nz(obs(P0 + [sh] + tail)) == {"vs_shove@deep": {outcome: 1}}, (sh, tail)
    # a non-shove open is vs_open, never vs_shove
    assert "vs_shove@deep" not in nz(obs(P0 + [H(0, "raise", 9999), H(1, "fold")]))


def test_limp_vs_raise_and_shove_vs_raise_are_distinct():
    assert nz(obs(P1 + [H(1, "call", 50), H(0, "check")])) == {"first_in@deep": {"limp": 1}}
    assert nz(obs(P1 + [H(1, "raise", 300), H(0, "fold")])) == {"first_in@deep": {"raise": 1}}
    assert nz(obs(P1 + [H(1, "raise", 10000), H(0, "fold")])) == {"first_in@deep": {"shove": 1}}


def test_cbet_outcomes_opponent_last_aggressor_acts_first():
    # opponent = seat 1 = big blind: we limp, it raises, we call, it acts first on the flop
    pre = [H(0, "post_small_blind", SB), H(1, "post_big_blind", BB),
           H(0, "call", 50), H(1, "raise", 400), H(0, "call", 300)]
    assert nz(obs(pre + [H(1, "check", 0, "flop")])) == {"cbet": {"check": 1}}
    for lab in ("bet", "raise"):                    # bench label, live label
        assert nz(obs(pre + [H(1, lab, 300, "flop"), H(0, "fold", 0, "flop")])) == {"cbet": {"bet": 1}}
    assert nz(obs(pre + [H(1, "fold", 0, "flop")])) == {"cbet": {"other": 1}}


def test_cbet_also_counts_when_the_opponent_acts_after_our_check():
    # literal spec: "its first flop action, if nobody was aggressive before it". Backed by the oracle:
    # only this reading gives the 24 Nov cbet counts (n=5 and n=2); an acts-first-only reading gives 3 and 1.
    h = P1 + [H(1, "raise", 250), H(0, "call", 150), H(0, "check", 0, "flop"), H(1, "bet", 300, "flop"),
              H(0, "fold", 0, "flop")]
    assert nz(obs(h)) == {"first_in@deep": {"raise": 1}, "cbet": {"bet": 1}, "checked_to": {"bet": 1}}


def test_cbet_not_counted_when_not_last_preflop_aggressor():
    # we 3-bet last: opponent is not the last aggressor (our open also makes a vs_open raise)
    h = P0 + [H(0, "raise", 250), H(1, "raise", 750), H(0, "raise", 2000), H(1, "call", 1250),
              H(1, "check", 0, "flop")]
    assert "cbet" not in nz(obs(h))


def test_cbet_not_counted_after_aggression_on_the_flop():
    # opponent (SB) raised last preflop, we (BB) bet the flop first: aggression before it
    h = P1 + [H(1, "raise", 250), H(0, "call", 150), H(0, "bet", 200, "flop"), H(1, "call", 200, "flop")]
    assert nz(obs(h)) == {"first_in@deep": {"raise": 1}, "vs_bet@1": {"call": 1}}


def test_checked_to_every_outcome_and_multi_street():
    base = P1 + [H(1, "call", 50), H(0, "check")]
    assert nz(obs(base + [H(0, "check", 0, "flop"), H(1, "check", 0, "flop")])) == {
        "first_in@deep": {"limp": 1}, "checked_to": {"check": 1}}
    assert nz(obs(base + [H(0, "check", 0, "flop"), H(1, "bet", 100, "flop"), H(0, "fold", 0, "flop")])) == {
        "first_in@deep": {"limp": 1}, "checked_to": {"bet": 1}}
    assert nz(obs(base + [H(0, "check", 0, "flop"), H(1, "fold", 0, "flop")])) == {
        "first_in@deep": {"limp": 1}, "checked_to": {"other": 1}}
    # flop check-check, turn check then opponent bets, river we bet and it raises
    h = base + [H(0, "check", 0, "flop"), H(1, "check", 0, "flop"),
                H(0, "check", 0, "turn"), H(1, "bet", 200, "turn"), H(0, "call", 200, "turn"),
                H(0, "bet", 400, "river"), H(1, "raise", 1200, "river"), H(0, "call", 800, "river")]
    assert nz(obs(h)) == {"first_in@deep": {"limp": 1},
                          "checked_to": {"check": 1, "bet": 1},
                          "vs_bet@3": {"raise": 1}}


def test_preflop_big_blind_check_is_not_checked_to():
    assert "checked_to" not in nz(obs(P1 + [H(1, "call", 50), H(0, "check")]))


def test_checked_to_needs_the_opponent_to_act_right_after_our_check():
    # opponent checks first (it is the big blind), we check behind: not checked_to for us
    h = P0 + [H(0, "call", 50), H(1, "check"), H(1, "check", 0, "flop"), H(0, "check", 0, "flop")]
    assert "checked_to" not in nz(obs(h))


def test_vs_bet_every_street_and_outcome():
    base = P1 + [H(1, "call", 50), H(0, "check")]
    for street, key in (("flop", "vs_bet@1"), ("turn", "vs_bet@2"), ("river", "vs_bet@3")):
        pre = []
        for s in ("flop", "turn", "river"):
            if s == street:
                break
            pre += [H(0, "check", 0, s), H(1, "check", 0, s)]     # earlier streets check through
        for tail, outcome in (([H(1, "fold", 0, street)], "fold"), ([H(1, "call", 100, street)], "call"),
                              ([H(1, "raise", 300, street), H(0, "fold", 0, street)], "raise"),
                              ([H(1, "check", 0, street)], "other")):
            st = obs(base + pre + [H(0, "bet", 100, street)] + tail)
            assert nz(st)[key] == {outcome: 1}, (street, tail, nz(st))


def test_vs_bet_every_aggressive_action_of_ours_counts_and_no_stored_total():
    h = P1 + [H(1, "call", 50), H(0, "check"),
              H(0, "bet", 100, "flop"), H(1, "raise", 300, "flop"), H(0, "raise", 900, "flop"),
              H(1, "fold", 0, "flop")]
    st = obs(h)
    assert nz(st)["vs_bet@1"] == {"raise": 1, "fold": 1}
    assert "vs_bet" not in st.counts          # the all-street total is derived, never stored


def test_our_all_in_label_is_aggression_postflop():
    h = P1 + [H(1, "call", 50), H(0, "check"), H(0, "all_in", 5000, "flop"), H(1, "fold", 0, "flop")]
    assert nz(obs(h))["vs_bet@1"] == {"fold": 1}


def test_fold_after_our_last_bet_round_end_path():
    h = P1 + [H(1, "call", 50), H(0, "check"),
              H(0, "bet", 100, "flop"), H(1, "call", 100, "flop"),
              H(0, "bet", 300, "turn"), H(1, "call", 300, "turn"),
              H(0, "bet", 800, "river"), H(1, "fold", 0, "river")]
    assert nz(obs(h)) == {"first_in@deep": {"limp": 1}, "vs_bet@1": {"call": 1},
                          "vs_bet@2": {"call": 1}, "vs_bet@3": {"fold": 1}}


def test_seat_swap_gives_identical_counts():
    hists = [P1 + [H(1, "raise", 250), H(0, "call", 150), H(0, "check", 0, "flop"),
                   H(1, "bet", 300, "flop"), H(0, "fold", 0, "flop")],
             P1 + [H(1, "call", 50), H(0, "check"), H(0, "bet", 100, "flop"), H(1, "fold", 0, "flop")]]
    for h in hists:
        a, b = obs(h, our=0), obs(swap(h), our=1)
        assert nz(a) == nz(b) and nz(a), (nz(a), nz(b))
    # and the perspective matters: the same history from the other seat is a different stat
    h = P1 + [H(1, "raise", 250), H(0, "fold")]
    assert nz(obs(h, our=0)) == {"first_in@deep": {"raise": 1}}
    assert nz(obs(h, our=1)) == {"vs_open@deep": {"fold": 1}}


def test_blinds_and_antes_excluded():
    # only posts: nothing is counted, and an opponent blind is not a first action
    assert nz(obs(P1)) == {}
    ante = [H(0, "post_ante", 10), H(1, "post_ante", 10), H(0, "ante", 10), H(1, "ante", 10)]
    assert nz(obs(ante + P1 + [H(1, "fold")])) == {"first_in@deep": {"fold": 1}}
    assert nz(obs(P1 + [H(1, "fold")])) == nz(obs(ante + P1 + [H(1, "fold")]))


def test_both_wires_same_hand_same_counts():
    live = P0 + [H(0, "raise", 10000), H(1, "call", 9900),
                 ]
    bench = P0 + [H(0, "all_in", 10000), H(1, "all_in", 9900)]
    a, b = obs(live), obs(bench)
    assert nz(a) == nz(b) == {"vs_shove@deep": {"call": 1}}
    # postflop bet labels: live "raise", bench "bet"
    pre = P1 + [H(1, "call", 50), H(0, "check")]
    x = pre + [H(0, "raise", 100, "flop"), H(1, "raise", 300, "flop"), H(0, "fold", 0, "flop")]
    y = pre + [H(0, "bet", 100, "flop"), H(1, "raise", 300, "flop"), H(0, "fold", 0, "flop")]
    assert nz(obs(x)) == nz(obs(y)) == {"first_in@deep": {"limp": 1}, "vs_bet@1": {"raise": 1}}


def test_hands_counter_and_accumulation():
    st = opmod.OpponentStats()
    for _ in range(3):
        st.observe_hand(P1 + [H(1, "fold")], 0, EFF, DEPTH)
    assert st.hands == 3 and st.errors == 0
    assert nz(st) == {"first_in@deep": {"fold": 3}}


def test_malformed_entries_never_raise_and_errors_rises():
    for bad in (None, [123], [{"action": "raise", "amount": 5, "phase": "preflop"}],
                [{"seat": 1, "action": "raise", "amount": "oops", "phase": "preflop"}]):
        st = opmod.OpponentStats()
        st.observe_hand(bad, 0, EFF, DEPTH)          # must not raise
        assert st.errors == 1, (bad, st.errors)
        st.observe_hand(P1 + [H(1, "fold")], 0, EFF, DEPTH)   # and the object stays usable
        assert st.errors == 1 and nz(st).get("first_in@deep") == {"fold": 1}, bad


def test_summary_reports_errors():
    st = opmod.OpponentStats()
    st.observe_hand(None, 0)
    assert st.summary().split()[:2] == ["hands=%d" % st.hands, "errors=1"]


# ---------- 2. sums ----------

def _summary_keys(line):
    toks = line.split()
    assert toks[0].startswith("hands=") and toks[1].startswith("errors="), line
    out = collections.OrderedDict()
    for t in toks[2:]:
        k, v = t.split("=")
        n, o = v.split(":")
        out[k] = (int(n), [int(x) for x in o.split("/")])
    return toks[0], toks[1], out


def _stream():
    return [
        P1 + [H(1, "fold")],
        P1 + [H(1, "call", 50), H(0, "check"), H(0, "check", 0, "flop"), H(1, "bet", 100, "flop"),
              H(0, "call", 100, "flop")],
        P1 + [H(1, "raise", 250), H(0, "call", 150), H(0, "bet", 200, "flop"), H(1, "raise", 600, "flop"),
              H(0, "fold", 0, "flop")],
        P0 + [H(0, "raise", 250), H(1, "call", 150), H(1, "check", 0, "flop"), H(0, "bet", 100, "flop"),
              H(1, "fold", 0, "flop")],
        P0 + [H(0, "raise", 10000), H(1, "fold")],
        P0 + [H(0, "raise", 250), H(1, "all_in", 10000), H(0, "fold")],
    ]


def test_outcomes_sum_to_opportunities_in_every_key():
    st = opmod.OpponentStats()
    for h in _stream():
        st.observe_hand(h, 0, EFF, DEPTH)
    assert st.errors == 0 and st.hands == len(_stream())
    _, _, keys = _summary_keys(st.summary())
    assert keys, "summary lists no key after six hands"
    for k, (n, o) in keys.items():
        assert n == sum(o) == sum(st.counts[k].values()), (k, n, o, st.counts[k])
        assert set(st.counts[k]) <= set(outs(k)), (k, st.counts[k])
        assert len(o) == len(outs(k)), (k, o)
    # hand-derived opportunities for this stream (opponent first_in x3; vs_open x3 ...):
    tot = lambda base: sum(sum(v.values()) for k, v in st.counts.items() if k.split("@")[0] == base)
    assert tot("first_in") == 3          # hands 1-3 (opponent is the small blind)
    assert tot("vs_open") == 2           # hands 4 and 6 (hand 5 is a shove)
    assert tot("vs_shove") == 1          # hand 5
    assert tot("vs_bet") == 2            # hand 3 (our flop bet, it raises) and hand 4 (our flop bet, it folds)
    assert tot("checked_to") == 1        # hand 2
    assert tot("cbet") == 0              # nobody is the opponent-last-aggressor with it acting first


def test_outcomes_table_matches_spec_order():
    want = {"first_in": ["fold", "limp", "raise", "shove", "other"],
            "vs_open": ["fold", "call", "raise", "shove", "other"],
            "vs_shove": ["fold", "call", "other"],
            "cbet": ["check", "bet", "other"], "checked_to": ["check", "bet", "other"],
            "vs_bet": ["fold", "call", "raise", "other"]}
    for k, v in want.items():
        assert outs(k) == v, (k, outs(k))


# ---------- 6. the STATS line format ----------

CANON = ["first_in", "vs_open", "vs_shove", "cbet", "checked_to", "vs_bet"]
BUCK = ["le10", "10to20", "deep", "na"]


def _rank(key):
    base, _, suf = key.partition("@")
    return (CANON.index(base), (BUCK + ["1", "2", "3"]).index(suf) if suf else 0)


def test_summary_exact_string_for_a_known_history():
    st = opmod.OpponentStats()
    # hand 1: opponent (SB) raises, we fold; hand 2: we (SB) open, it calls, we bet the flop, it folds
    st.observe_hand(P1 + [H(1, "raise", 250), H(0, "fold")], 0, EFF, DEPTH)
    st.observe_hand(P0 + [H(0, "raise", 250), H(1, "call", 150), H(1, "check", 0, "flop"),
                          H(0, "bet", 100, "flop"), H(1, "fold", 0, "flop")], 0, EFF, DEPTH)
    line = st.summary()
    assert "\n" not in line
    stripped = " ".join(t for t in line.split() if not re.match(r"[^=]+=0:", t))
    # hands 2, errors 0; first_in@deep raise 1 (fold/limp/raise/shove/other = 0/0/1/0/0);
    # vs_open@deep call 1 (fold/call/raise/shove/other = 0/1/0/0/0); vs_bet@1 fold 1 (0..: fold/call/raise/other = 1/0/0/0)
    assert stripped == ("hands=2 errors=0 first_in@deep=1:0/0/1/0/0 vs_open@deep=1:0/1/0/0/0 "
                        "vs_bet@1=1:1/0/0/0"), line
    ranks = [_rank(t.split("=")[0]) for t in line.split()[2:]]
    assert ranks == sorted(ranks), line            # fixed key order


def test_empty_summary_starts_with_hands_and_errors():
    assert opmod.OpponentStats().summary().split()[:2] == ["hands=0", "errors=0"]


# ---------- one parser ----------

def test_parse_actions_excludes_blinds_and_antes_by_length():
    h = [H(0, "post_ante", 10), H(1, "post_ante", 10)] + P1 + [H(1, "raise", 250), H(0, "call", 150),
         H(0, "check", 0, "flop"), H(1, "check", 0, "flop")]
    assert len(opmod.parse_actions(h, 0)) == 4
    assert len(opmod.parse_actions(h, 1)) == 4
    assert len(opmod.parse_actions(P1, 0)) == 0


def test_villain_raises_and_calls_agree_with_hand_counts_on_same_histories():
    from chipzen import GameState
    from chipzen.models import Card
    import bot as botmod

    def state(hist, your_seat):
        return GameState(hand_number=1, dealer_seat=0, your_seat=your_seat, opponent_stacks=[1000],
                         action_history=[dict(e, is_timeout=False) for e in hist], phase="preflop",
                         hole_cards=[Card.from_str("As"), Card.from_str("Ad")], board=[], pot=300,
                         to_call=100, min_raise=200, max_raise=1000, your_stack=1000,
                         valid_actions=["fold", "call"])
    # (history, our seat, villain raises, villain calls), derived by hand
    h1 = P0 + [H(0, "raise", 300), H(1, "call", 200), H(1, "check", 0, "flop"), H(0, "bet", 200, "flop"),
               H(1, "raise", 600, "flop"), H(0, "call", 400, "flop"), H(1, "check", 0, "turn"),
               H(0, "check", 0, "turn")]
    cases = [(h1, 0, 1, 1), (h1, 1, 2, 1), (P0, 0, 0, 0),
             (P0 + [H(0, "call", 50), H(1, "check")], 0, 0, 0),
             (P0 + [H(0, "call", 50), H(1, "raise", 300), H(0, "call", 200)], 1, 1, 1)]
    for hist, seat, raises, calls in cases:
        assert botmod._villain_raises(state(hist, seat)) == raises, (hist, seat)
        assert botmod._villain_calls(state(hist, seat)) == calls, (hist, seat)
        n_vol = len([e for e in hist if not e["action"].startswith("post_")])
        assert len(opmod.parse_actions(hist, seat)) == n_vol


# ---------- bot.py wiring: STATS line cadence, reset, match end, flag ----------

class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, r):
        m = r.getMessage()
        if m.startswith("STATS "):
            self.lines.append(m[len("STATS "):])


class capture:
    def __enter__(self):
        self.lg, self.h = logging.getLogger("pokercpp"), _Cap()
        self.old = self.lg.level
        self.lg.setLevel(logging.INFO)
        self.lg.addHandler(self.h)
        return self.h

    def __exit__(self, *a):
        self.lg.removeHandler(self.h)
        self.lg.setLevel(self.old)


def _result(n, hist=None):
    hist = hist or (P1 + [H(1, "fold")])
    return {"type": "round_result", "result": {
        "hand_number": n, "winner_seats": [0], "pot": 150, "payouts": [{"seat": 0, "amount": 150}],
        "showdown": [], "action_history": hist, "stacks": [10050, 9950]}}


def _bot():
    import bot as botmod
    b = botmod.PokerCppBot()
    b.on_match_start({"game_config": {"small_blind": 50, "big_blind": 100, "ante": 0, "starting_stack": 10000}})
    b.my_seat = 0
    return botmod, b


def test_stats_line_every_ten_hands_match_end_and_reset():
    botmod, b = _bot()
    with capture() as cap:
        for n in range(1, 10):
            b.on_round_start({})
            b.on_round_result(_result(n))
        assert cap.lines == [], cap.lines
        b.on_round_result(_result(10))
        assert len(cap.lines) == 1 and cap.lines[0].startswith("hands=10 errors=0 "), cap.lines
        assert "first_in@" in cap.lines[0]
        b.on_round_result(_result(11))
        b.on_match_end({})
        assert cap.lines[-1].startswith("hands=11 "), cap.lines
        # reset at match start: the count starts again
        b.on_match_start({"game_config": {"small_blind": 50, "big_blind": 100, "ante": 0,
                                          "starting_stack": 10000}})
        n0 = len(cap.lines)
        for n in range(1, 11):
            b.on_round_result(_result(n))
        assert len(cap.lines) == n0 + 1 and cap.lines[-1].startswith("hands=10 "), cap.lines


def test_stats_disabled_flag_logs_nothing():
    botmod, b = _bot()
    old = botmod.STATS_ENABLED
    try:
        with capture() as cap:                      # positive control: the same run logs when enabled
            for n in range(1, 11):
                b.on_round_result(_result(n))
        assert cap.lines, "no STATS line with the flag on"
        botmod.STATS_ENABLED = False
        with capture() as cap:
            for n in range(1, 21):
                b.on_round_result(_result(n))
            b.on_match_end({})
        assert cap.lines == []
    finally:
        botmod.STATS_ENABLED = old


# ---------- 3 and 4. the round-end path and the no-play-change spy, in bench ----------

def _bench():
    import pokercpp_engine
    import bench
    return bench, pokercpp_engine


def _last_stats(lines):
    assert lines, "bot logged no STATS line"
    hands, errors, keys = _summary_keys(lines[-1])
    return int(hands.split("=")[1]), int(errors.split("=")[1]), {k: v[1] for k, v in keys.items()}


def _run_bench(wire, stack_bb, hands=200, flag=True, sims=150):
    """Run --hero bot (bench.Bot, the real chipzen/bot.py) vs reference. Returns the bot's log
    lines (the STATS line is captured from the bot's logger; bench exposes no stats object by
    name), the engine kwargs of every decide() call and the pair results."""
    bench, eng = _bench()
    import bot as botmod
    old_flag, old_dec = getattr(botmod, "STATS_ENABLED", None), eng.decide
    botmod.STATS_ENABLED = flag
    kwlog = []
    try:
        with capture() as cap:
            hero = bench.Bot(50, 100, stack_bb * 100, sims=sims, wire=wire)
            inner = eng.decide

            def spy(**kw):
                kwlog.append(repr(sorted(kw.items())))
                return inner(**kw)
            eng.decide = spy
            res = bench.duplicate_match(hands, hero, bench.OPPONENTS["reference"](),
                                        blinds=(50, 100), stack=stack_bb * 100, seed0=1)
        return list(cap.lines), kwlog, res
    finally:
        eng.decide = old_dec
        if old_flag is not None:
            botmod.STATS_ENABLED = old_flag


def _by_base(keys):
    out = collections.defaultdict(int)
    for k, o in keys.items():
        out[k.split("@")[0]] += sum(o)
    return out


def test_bench_round_end_path_every_preflop_situation_both_wires():
    # 10 bb deep so that the hero both opens and shoves (checked in advance with a hand counter)
    got = {}
    for wire in ("live", "bench"):
        lines, _, _ = _run_bench(wire, 10)
        hands, errors, keys = _last_stats(lines)
        assert hands == 200 and errors == 0, (wire, hands, errors)
        n = _by_base(keys)
        for situation in ("first_in", "vs_open", "vs_shove"):
            assert n[situation] > 0, (wire, situation, dict(n))
        got[wire] = keys
    assert got["live"] == got["bench"], "counts differ between the two wires on the same seed"


def test_bench_counts_agree_across_wires_at_100bb():
    a = _last_stats(_run_bench("live", 100)[0])
    b = _last_stats(_run_bench("bench", 100)[0])
    assert a == b and a[0] == 200 and a[1] == 0
    n = _by_base(a[2])
    assert n["first_in"] > 0 and n["vs_open"] > 0


def test_no_play_change_stats_on_vs_off_both_wires():
    for wire in ("live", "bench"):
        on_lines, on_kw, on_res = _run_bench(wire, 25, hands=60, flag=True)
        off_lines, off_kw, off_res = _run_bench(wire, 25, hands=60, flag=False)
        assert on_lines and off_lines == [], (wire, len(on_lines), len(off_lines))
        assert len(on_kw) > 0 and on_kw == off_kw, (wire, "decide() kwargs differ with stats on/off")
        assert on_res == off_res, wire


# ---------- 5. the oracle: replay the 24 Nov live logs (FIDELITY, not correctness) ----------

LOGS = os.path.join(ROOT, "results", "live-logs")
M1, M2 = "2026-11-24_222814-live.log", "2026-11-24_223520-live2.log"


def _replay(name):
    import live_log_histories as L
    hands, final = L.parse(os.path.join(LOGS, name))
    st = opmod.OpponentStats()
    for h in hands:
        st.observe_hand(h["history"], 0, h["eff"], h["depth_bb"])      # seat 0 is us in both
    return st, hands, final


def _tot(st, base, extra=None):
    out = collections.Counter()
    for k, v in st.counts.items():
        if k.split("@")[0] == base and (extra is None or k == extra):
            out.update(v)
    return {o: n for o, n in out.items() if n}


# results/2026-11-24-live-log-analysis.md section 1, zero cells dropped
ORACLE = {
    M1: {"first_in": {"fold": 7, "limp": 12, "raise": 24, "shove": 2},
         "vs_open": {"fold": 5, "call": 16, "raise": 1},
         "vs_shove": {"fold": 1, "call": 1},
         "cbet": {"check": 3, "bet": 2}, "checked_to": {"bet": 7, "check": 9}},
    M2: {"first_in": {"fold": 39, "limp": 3, "raise": 5},
         "vs_open": {"fold": 24, "call": 2, "shove": 1},
         "vs_shove": {},
         "cbet": {"check": 2}, "checked_to": {"check": 7}},
}
ORACLE_BET = {
    M1: {"vs_bet@1": {"fold": 9, "call": 5, "raise": 1}, "vs_bet@2": {"fold": 4, "call": 3},
         "vs_bet@3": {"fold": 2, "call": 4, "raise": 1}},
    M2: {"vs_bet@1": {"fold": 5, "call": 5}, "vs_bet@2": {"fold": 2, "call": 3},
         "vs_bet@3": {"fold": 3, "call": 4}},
}


def test_oracle_parser_self_check_chips_conserved_and_match_result():
    # the tester's own log parser: the chained stacks must end where the matches ended
    import live_log_histories as L
    hands1, final1 = L.parse(os.path.join(LOGS, M1))
    assert len(hands1) == 90 and final1 == [0, 20000], final1       # match 1: lost 10000
    hands2, final2 = L.parse(os.path.join(LOGS, M2))
    assert len(hands2) == 95 and final2 == [20000, 0], final2        # match 2: won 10000


def _oracle(name):
    st, hands, _ = _replay(name)
    assert st.errors == 0 and st.hands == len(hands)
    diffs = []
    for base, want in ORACLE[name].items():
        got = _tot(st, base)
        if got != want:
            diffs.append((base, "want", want, "got", got))
    for key, want in ORACLE_BET[name].items():
        got = _tot(st, "vs_bet", key)
        if got != want:
            diffs.append((key, "want", want, "got", got))
    assert not diffs, "differences from section 1 (stated, not tuned): " + repr(diffs)


def test_oracle_fidelity_match1_vs_open_and_table():
    _oracle(M1)


def test_oracle_fidelity_match2_vs_open_and_table():
    _oracle(M2)


if __name__ == "__main__":
    run(globals())
