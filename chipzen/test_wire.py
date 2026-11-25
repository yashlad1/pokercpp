"""Black-box checks for bot.py: crash-proof decide, villain raise counting,
legality of _to_action, and the POKERCPP_SIMS variable.

Run from the repo root:  PYTHONPATH=chipzen python chipzen/test_wire.py
"""
import itertools, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["POKERCPP_SIMS"] = "2000"

from chipzen import GameState
from chipzen.models import Card
import bot as botmod


def C(s): return Card.from_str(s)


def H(seat, action, amount=0):
    return {"seat": seat, "action": action, "amount": amount,
            "phase": "preflop", "is_timeout": False}


def state(valid, hist=(), your_seat=1, to_call=100, min_raise=200,
          max_raise=1000, pot=300, stack=1000):
    return GameState(hand_number=1, dealer_seat=0, your_seat=your_seat,
                     opponent_stacks=[1000], action_history=list(hist),
                     phase="preflop", hole_cards=[C("As"), C("Ad")], board=[],
                     pot=pot, to_call=to_call, min_raise=min_raise,
                     max_raise=max_raise, your_stack=stack, valid_actions=list(valid))


# ---- gap 1: decide never raises, always legal --------------------------------
VALID_SETS = [
    ["fold", "call", "raise"], ["check", "raise"], ["check"], ["fold", "call"],
    ["call", "raise"], ["call"], ["all_in"], ["fold", "all_in"],
]


def test_decide_survives_engine_failure():
    real = botmod.pokercpp_engine.decide

    def boom(*a, **k):
        raise RuntimeError("engine down")

    botmod.pokercpp_engine.decide = boom
    try:
        bad = []
        for valid in VALID_SETS:
            tc = 0 if "check" in valid else 100
            mn, mx = (200, 1000) if "raise" in valid else (0, 0)
            st = state(valid, hist=[H(0, "post_small_blind", 50), H(1, "post_big_blind", 100)],
                       to_call=tc, min_raise=mn, max_raise=mx)
            try:
                act = botmod.PokerCppBot().decide(st)
            except Exception as e:  # noqa: BLE001
                bad.append("%s raised %s: %s" % (valid, type(e).__name__, e))
                continue
            if act.action not in valid:
                bad.append("%s -> illegal %s" % (valid, act.action))
        assert not bad, "; ".join(bad)
    finally:
        botmod.pokercpp_engine.decide = real


# ---- gap 5: _to_action legality ----------------------------------------------
ENGINE = {"fold": {"action": "fold"}, "check": {"action": "check"},
          "call": {"action": "call"},
          "raise 300": {"action": "raise", "amount": 300},
          "raise 99999": {"action": "raise", "amount": 99999}}
KINDS = ["fold", "check", "call", "raise", "all_in"]
BOUNDS = [(200, 1000), (400, 300), (0, 0)]


def nothing_legal(valid, mn, mx):
    # raise is only takeable with a band; every other kind is always takeable
    return set(valid) == {"raise"} and mn == 0 and mx == 0


def legal_problem(act, valid, mn, mx):
    if nothing_legal(valid, mn, mx):
        return None if act.action == "fold" else "nothing legal: want fold, got %s" % act.action
    if act.action not in valid:
        return "kind %s not in valid" % act.action
    if act.action == "raise":
        amt = act.amount
        if mn > 0 and mx > 0 and mn > mx and amt != mx:
            return "short stack: raise %s, want exactly %s" % (amt, mx)
        if mn > 0 and mx > 0 and mn <= mx and not (mn <= amt <= mx):
            return "raise %s outside [%s,%s]" % (amt, mn, mx)
        if mn == 0 and mx == 0 and not amt:
            return "raise of 0"
    return None


def test_to_action_is_always_legal():
    fails, total = [], 0
    for n in range(1, 6):
        for valid in itertools.combinations(KINDS, n):
            valid = list(valid)
            for name, d in ENGINE.items():
                for mn, mx in BOUNDS:
                    for tc in (0, 100):
                        total += 1
                        st = state(valid, to_call=tc, min_raise=mn, max_raise=mx)
                        try:
                            act = botmod.PokerCppBot()._to_action(dict(d), st, valid)
                            why = legal_problem(act, valid, mn, mx)
                        except Exception as e:  # noqa: BLE001
                            why = "raised %s: %s" % (type(e).__name__, e)
                        if why:
                            fails.append("reply=%r valid=%s bounds=(%d,%d) to_call=%d: %s"
                                         % (name, valid, mn, mx, tc, why))
    assert not fails, "%d of %d combinations illegal; first 3: %s" % (
        len(fails), total, " | ".join(fails[:3]))


# ---- gap 9: POKERCPP_SIMS -----------------------------------------------------
def sims_after_import(value):
    env = dict(os.environ, PYTHONPATH=HERE, POKERCPP_SIMS=value)
    return subprocess.run([sys.executable, "-c", "import bot; print(bot.SIMS)"],
                          env=env, cwd=HERE, capture_output=True, text=True)


def _sims(v, want):
    r = sims_after_import(v)
    assert r.returncode == 0, "POKERCPP_SIMS=%r crashed import: %s" % (v, r.stderr.strip()[-200:])
    assert r.stdout.strip() == want, "POKERCPP_SIMS=%r gave SIMS %r" % (v, r.stdout.strip())


def test_sims_abc_falls_back():
    _sims("abc", "5000")


def test_sims_empty_falls_back():
    _sims("", "5000")


def test_sims_numeric_still_works():
    r = sims_after_import("2000")
    assert r.returncode == 0, r.stderr.strip()[-200:]
    assert r.stdout.strip() == "2000", r.stdout


def run():
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except BaseException as e:  # noqa: BLE001
                failed += 1
                print("FAIL", name, "-", type(e).__name__, e)
    if failed:
        print(failed, "failed")
        sys.exit(1)
    print("all passed")


if __name__ == "__main__":
    run()
