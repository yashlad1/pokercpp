# Replay live turn states (chipzen/fixtures/live-*.jsonl) through decide().
# Run from chipzen/:  python test_replay.py
# Test another bot.py:  BOT_PY=/path/to/bot.py python test_replay.py
import os, sys, json, glob, time, logging, importlib.util, collections
os.environ["POKERCPP_SIMS"] = "2000"
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
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().addHandler(H())

MAX_MS = 100
fails = []
def check(label, ok, detail=""):
    if not ok:
        fails.append(label)
        print("FAIL " + label + " :: " + str(detail))

def state_of(rec):
    d = {k: v for k, v in rec.items() if k not in ("match_file", "live")}
    d["hole_cards"] = [Card.from_str(c) for c in d["hole_cards"]]
    d["board"] = [Card.from_str(c) for c in d["board"]]
    d.setdefault("your_seat", 0)  # dropped from the fixture when always 0 -- kept, but be safe
    return GameState(**d)

def history_bb(rec):
    for e in rec["action_history"]:
        if e["action"] == "post_big_blind":
            return e["amount"]
    return None

recs = [json.loads(l) for p in sorted(glob.glob(os.path.join(HERE, "fixtures", "live-*.jsonl"))) for l in open(p)]
by_match = collections.OrderedDict()
for r in recs:
    by_match.setdefault(r["match_file"], []).append(r)

same = n = 0
times = []
for mf, rs in by_match.items():
    b = bot.PokerCppBot()  # fresh bot per match, states in the logged order
    b.on_match_start({})
    for r in rs:
        n += 1
        tag = "%s hand %s %s" % (mf[:17], r["hand_number"], r["phase"])
        st, mark = state_of(r), len(records)
        t0 = time.perf_counter()
        try:
            a = b.decide(st)
        except Exception as e:
            check(tag + " no exception", False, repr(e)); continue
        ms = (time.perf_counter() - t0) * 1000
        times.append(ms)
        msgs = [x.getMessage() for x in records[mark:]]
        valid = r["valid_actions"]
        check(tag + " action in valid_actions", a.action in valid, (a.action, valid))
        if a.action == "raise":
            lo, hi = bot._raise_band(st, valid)
            check(tag + " raise within band", lo <= a.amount <= hi, (a.amount, lo, hi))
        real = history_bb(r) or r["live"]["bb"]
        check(tag + " logged bb matches history", history_bb(r) in (None, r["live"]["bb"]), (history_bb(r), r["live"]["bb"]))
        check(tag + " derived bb == real bb", b._bb(st) == real, (b._bb(st), real))
        check(tag + " no ENGINE FAILED", not any("ENGINE FAILED" in m for m in msgs))
        check(tag + " under %d ms" % MAX_MS, ms < MAX_MS, "%.1f ms" % ms)
        same += (a.action == r["live"]["action"]
                 and (a.action != "raise" or a.amount == r["live"]["amount"]))

times.sort()
print("states=%d matches=%d" % (n, len(by_match)))
print("replay == live action: %d/%d (%.0f%%), informational" % (same, n, 100 * same / max(n, 1)))
print("decision ms: median %.1f p95 %.1f max %.1f" % (times[len(times)//2], times[int(len(times)*.95)], times[-1]))
print(("FAIL: %d checks failed" % len(fails)) if fails else "PASS: all %d states" % n)
sys.exit(1 if fails else 0)
