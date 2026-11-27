import os, sys, re, json, logging, dataclasses, subprocess
os.environ["POKERCPP_SIMS"] = "2000"
import bot
from chipzen import GameState
from chipzen.models import Card

records = []
class H(logging.Handler):
    def emit(self, r): records.append(r)
root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(H())

BBRE = re.compile(r"(?<![A-Za-z_])bb=(\d+)")
fails = []

def report(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " :: " + str(detail)))
    if not ok:
        fails.append(name)

def newbot():
    return bot.PokerCppBot()

def cards(*s):
    return [Card.from_str(x) for x in s]

def gs(**kw):
    d = dict(your_seat=0, dealer_seat=0, hand_number=0, phase="preflop",
             hole_cards=cards("Ah", "Kd"), board=[], pot=150, to_call=50,
             min_raise=200, max_raise=10000, your_stack=9950,
             valid_actions=["fold", "call", "raise"], action_history=[],
             opponent_stacks=[9900])
    d.update(kw)
    return GameState(**d)

def decide_bb(b, st):
    n = len(records)
    b.decide(st)
    bbs = [int(m.group(1)) for r in records[n:] if " -> " in r.getMessage()
           and (m := BBRE.search(r.getMessage()))]
    return bbs[-1] if bbs else None

def new(n):
    return records[n:]

OPEN = {"seat":0,"action":"raise","amount":250,"phase":"preflop","is_timeout":False}
THREE = {"seat":1,"action":"raise","amount":750,"phase":"preflop","is_timeout":False}
CALL = {"seat":0,"action":"call","amount":500,"phase":"preflop","is_timeout":False}

def d2(hist):
    return gs(pot=1000, to_call=500, min_raise=1250, your_stack=9750,
              opponent_stacks=[9250], action_history=hist)

def safe(name, fn):
    try:
        fn()
    except Exception as e:
        import traceback
        report(name, False, "exception " + traceback.format_exc(limit=3))

def t1():
    b = newbot()
    r = [decide_bb(b, gs())]
    r.append(decide_bb(b, d2([OPEN, THREE])))
    r.append(decide_bb(b, gs(phase="flop", board=cards("2c", "7d", "9h"), pot=1500,
        to_call=0, valid_actions=["check", "raise"], min_raise=100, max_raise=9250,
        your_stack=9250, opponent_stacks=[9250], action_history=[OPEN, THREE, CALL])))
    report("T1", r == [100, 100, 100], r)

def rs(n):
    return {"type":"round_start","round_id":f"r{n}","round_number":n,"state":{
        "hand_number":0,"dealer_seat":0,"your_hole_cards":["Ah","Kd"],"stacks":[9950,9900]}}

def t2_t3():
    b = newbot()
    b.on_round_start(rs(1))
    r = [decide_bb(b, gs()), decide_bb(b, d2([]))]
    report("T2", r == [100, 100], r)
    b.on_round_start(rs(2))
    r3 = decide_bb(b, gs(pot=300, to_call=100, min_raise=400, your_stack=9800))
    report("T3", r3 == 200, r3)

def t4():
    b = newbot()
    b.on_match_start({"game_config":{"small_blind":50,"big_blind":100,"ante":0,"starting_stack":10000}})
    n = len(records)
    v = decide_bb(b, gs(your_seat=1, dealer_seat=None, hand_number=5, your_stack=9900))
    warn = any(r.levelno == logging.WARNING and "dealer_seat missing" in r.getMessage() for r in new(n))
    report("T4", v == 100 and warn, f"bb={v} warn={warn}")

def t5():
    b = newbot(); n = len(records)
    decide_bb(b, gs(hand_number=7, min_raise=300))
    w = any(r.levelno == logging.WARNING and "BB MISMATCH" in r.getMessage() for r in new(n))
    b = newbot(); n = len(records)
    decide_bb(b, gs(hand_number=7, min_raise=200))
    w2 = any("BB MISMATCH" in r.getMessage() for r in new(n))
    report("T5", w and not w2, f"mismatch_warn={w} clean_has_warn={w2}")

def t6():
    keys = {f.name for f in dataclasses.fields(GameState)}
    b = newbot(); b.on_match_start({}); n = len(records)
    for i in range(1, 61):
        b.decide(gs(hand_number=i))
    st = [r.getMessage() for r in new(n) if r.levelno == logging.INFO and r.getMessage().startswith("STATE ")]
    ok = len(st) == 50
    detail = f"count={len(st)}"
    if st:
        try:
            for m in st:
                j = json.loads(m[len("STATE "):])
                assert set(j) == keys, (set(j) ^ keys)
                hc = j["hole_cards"]
                assert isinstance(hc, list) and len(hc) == 2 and all(isinstance(c, str) and len(c) == 2 for c in hc), hc
        except Exception as e:
            ok = False; detail += f" parse: {e!r}"
    b.on_match_start({}); n = len(records)
    for i in range(1, 4):
        b.decide(gs(hand_number=i))
    c2 = len([r for r in new(n) if r.getMessage().startswith("STATE ")])
    report("T6", ok and c2 == 3, detail + f" after_reset={c2}")

def t7():
    env = {k: v for k, v in os.environ.items()
           if k not in ("CHIPZEN_WS_URL", "CHIPZEN_URL", "CHIPZEN_TOKEN", "CHIPZEN_TICKET")}
    env["POKERCPP_COMMIT"] = "abc1234"
    p = subprocess.run([sys.executable, bot.__file__], env=env, capture_output=True,
                       text=True, timeout=60)
    out = p.stdout + p.stderr
    import pokercpp_engine
    bi = pokercpp_engine.build_info()
    want = "pokercpp v%s commit=abc1234 engine=%s preflop=%s call_narrow=%s" % (
        bot.VERSION, bi["git_sha"], bi["preflop_realization"], bi["call_narrow"])
    report("T7", p.returncode == 2 and want in out,
           f"rc={p.returncode} out={out[-300:]!r}")

def t8():
    b = newbot()
    r = [decide_bb(b, gs()), decide_bb(b, d2([OPEN, THREE]))]
    r.append(decide_bb(b, gs(pot=300, to_call=100, min_raise=400, your_stack=9800)))
    report("T8", r == [100, 100, 200], r)

BL = [{"seat":0,"action":"post_small_blind","amount":50,"phase":"preflop","is_timeout":False},
      {"seat":1,"action":"post_big_blind","amount":100,"phase":"preflop","is_timeout":False}]
SHOVE = BL + [{"seat":0,"action":"raise","amount":1500,"phase":"preflop","is_timeout":False}]

def shove_spot(hole):
    return GameState(hand_number=0, dealer_seat=0, your_seat=1, opponent_stacks=[0],
        action_history=list(SHOVE), phase="preflop", hole_cards=cards(hole[:2], hole[2:]),
        board=[], pot=1600, to_call=1400, min_raise=0, max_raise=0, your_stack=1400,
        valid_actions=["fold", "call"])

def rs9(k):
    return {"type":"round_start","round_id":"r","round_number":k,"state":{
        "hand_number":0,"dealer_seat":0,"your_hole_cards":[],"stacks":[1500,1500]}}

def t9():
    b = newbot(); b.on_round_start(rs9(1))
    a = b.decide(shove_spot("Ks8h")).action
    b = newbot()
    for k in range(1, 21):
        b.on_round_start(rs9(k)); b.decide(shove_spot("7h2c"))
    b.on_round_start(rs9(21))
    c = b.decide(shove_spot("Ks8h")).action
    report("T9", a == "fold" and c == "call", f"unknown={a} shover={c}")

def t10():
    b = newbot(); b.on_match_start({})
    h = lambda s, a, am, ph="preflop": {"seat":s,"action":a,"amount":am,"phase":ph,"is_timeout":False}
    hist = [h(0,"post_small_blind",200), h(1,"post_big_blind",400), h(0,"raise",1000),
            h(1,"raise",1600), h(0,"call",600), h(1,"raise",3115,"flop")]
    st = gs(hand_number=89, phase="flop", board=cards("Ah","Kd","7c"), hole_cards=cards("As","Ad"),
            pot=6315, to_call=3115, min_raise=6230, max_raise=3932, your_stack=3932,
            opponent_stacks=[9753], action_history=hist)
    a = b.decide(st)
    print("T10 action=%s amount=%s" % (a.action, a.amount))
    ok = a.action in st.valid_actions and a.action != "fold" and (a.action != "raise" or a.amount == 3932)
    report("T10", ok, f"action={a.action} amount={a.amount}")

for name, f in [("T1", t1), ("T2/T3", t2_t3), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7), ("T8", t8), ("T9", t9), ("T10", t10)]:
    safe(name, f)

if fails:
    print("v4 tests FAILED:", fails); sys.exit(1)
print("v4 tests: all passed")
