# Run from chipzen/:  python test_logging.py
# Test another bot.py:  BOT_PY=/path/to/bot.py python test_logging.py
import os, sys, json, logging, importlib.util
os.environ["POKERCPP_SIMS"] = "2000"
os.environ["POKERCPP_COMMIT"] = "abc1234"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("bot", os.environ.get("BOT_PY", os.path.join(HERE, "bot.py")))
bot = importlib.util.module_from_spec(_spec)
sys.modules["bot"] = bot
_spec.loader.exec_module(bot)
from chipzen import GameState
from chipzen.models import Card

records = []
class H(logging.Handler):
    def emit(self, r): records.append(r)
root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(H())

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
        report(name, False, "exception " + traceback.format_exc(limit=3))

def msgs(n):
    return [r.getMessage() for r in records[n:]]

def cards(*s):
    return [Card.from_str(x) for x in s]

def gs(**kw):
    d = dict(your_seat=0, dealer_seat=0, hand_number=0, phase="preflop",
             hole_cards=cards("Jc", "Jd"), board=[], pot=150, to_call=50,
             min_raise=200, max_raise=10000, your_stack=9950,
             valid_actions=["fold", "call", "raise"], action_history=[],
             opponent_stacks=[9900])
    d.update(kw)
    return GameState(**d)

RESULT = {"hand_number": 13, "winner_seats": [1], "pot": 13300,
          "payouts": [{"seat": 1, "amount": 13300}],
          "showdown": [{"seat": 0, "hole_cards": ["Jc", "Jd"], "hand_rank": "pair", "best_hand": ["Jc", "Jd", "5c", "9d", "4d"]},
                       {"seat": 1, "hole_cards": ["7h", "8h"], "hand_rank": "straight", "best_hand": ["7h", "8h", "9d", "5c", "6s"]}],
          "stacks": [0, 20000], "deck_reveal": None,
          "action_history": [{"seat": 0, "action": "call", "amount": 50, "phase": "preflop"}]}
MSG = {"type": "round_result", "round_id": "r", "round_number": 13, "result": RESULT}

def round_lines():
    b = bot.PokerCppBot(); b.on_match_start({}); n = len(records)
    b.on_round_result(json.loads(json.dumps(MSG)))
    return msgs(n)

def round_json():
    ls = [m for m in round_lines() if m.startswith("ROUND ")]
    assert len(ls) == 1, ls
    return json.loads(ls[0][len("ROUND "):])

def s1_version_line():
    b = bot.PokerCppBot(); n = len(records)
    b.on_match_start({})
    want = "pokercpp v%s commit=abc1234" % bot.VERSION
    report("spec1 version+commit line", want in msgs(n), msgs(n))
    report("spec1 match_start line kept", any(m.startswith("match_start seats=") for m in msgs(n)), msgs(n))

def s1_default_unknown():
    os.environ.pop("POKERCPP_COMMIT")
    try:
        n = len(records); bot.PokerCppBot().on_match_start({})
        want = "pokercpp v%s commit=unknown" % bot.VERSION
        report("spec1 commit defaults to unknown", want in msgs(n), msgs(n))
    finally:
        os.environ["POKERCPP_COMMIT"] = "abc1234"

def s2_round_json():
    j = round_json()
    report("spec2 ROUND has no action_history", "action_history" not in j, list(j))
    report("spec2 ROUND keeps seat1 hole_cards", [s for s in j["showdown"] if s["seat"] == 1][0]["hole_cards"] == ["7h", "8h"], j.get("showdown"))
    report("spec2 ROUND keeps stacks and payouts", j["stacks"] == [0, 20000] and j["payouts"] == [{"seat": 1, "amount": 13300}], j)
    exp = {k: v for k, v in RESULT.items() if k != "action_history"}
    report("spec2 ROUND equals result minus action_history", j == exp, j)

def s2_round_result_line():
    ls = [m for m in round_lines() if m.startswith("round_result ")]
    report("spec2 round_result line still says showdown=2", len(ls) == 1 and "showdown=2" in ls[0], ls)

def s2_none():
    b = bot.PokerCppBot()
    b.on_round_result(None)
    b.on_round_result({"type": "round_result"})
    report("spec2 None/no-result message does not raise", True)

def s3_board():
    b = bot.PokerCppBot(); n = len(records)
    b.decide(gs())
    pre = [m for m in msgs(n) if "hole=" in m and "legal=" in m]
    report("spec3 preflop board=-", len(pre) >= 1 and all("hole=JcJd board=- legal=" in m for m in pre), pre)
    n = len(records)
    b.decide(gs(phase="flop", board=cards("5c", "9d", "4d"), pot=1500, to_call=0,
                valid_actions=["fold", "call", "raise"], min_raise=100, max_raise=9250,
                your_stack=9250, opponent_stacks=[9250]))
    fl = [m for m in msgs(n) if "hole=" in m and "legal=" in m]
    report("spec3 flop board=5c9d4d", len(fl) >= 1 and all("hole=JcJd board=5c9d4d legal=" in m for m in fl), fl)

for name, f in [("s1", s1_version_line), ("s1d", s1_default_unknown), ("s2", s2_round_json),
                ("s2l", s2_round_result_line), ("s2n", s2_none), ("s3", s3_board)]:
    safe(name, f)

if fails:
    print("logging tests FAILED:", fails); sys.exit(1)
print("logging tests: all passed")
