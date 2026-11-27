"""Per-match memory of how often the opponent raises, so the engine can widen its range guess for
one who raises every hand (whose third raise is no stronger than the first)."""

# ponytail: fitted, not measured. Pseudo-hands of no raise, so a couple of
# hands cannot swing the range. 3 and not 20 because a short-stacked freezeout
# against a shover can be over in a dozen hands, and 20 would never get going.
# ponytail: hands where villain folds before we act are never seen, so the
# rate is overstated against tight opponents. Fine while the floor only
# widens past the step function for very aggressive opponents.
PRIOR_HANDS = 3


class Opponent:
    """Counts, per hand, the most raises villain made as seen at our turns."""

    def __init__(self):
        self.max_raises_by_hand = {}  # hand id -> most raises villain made in it, as seen at our turns

    def saw(self, hand, villain_raises):
        self.max_raises_by_hand[hand] = max(self.max_raises_by_hand.get(hand, 0), villain_raises)

    def range_floor(self, villain_raises):
        """Fraction of hands in which villain made at least this many raises."""
        if villain_raises < 1:
            return 0.0
        hits = sum(r >= villain_raises for r in self.max_raises_by_hand.values())
        return hits / (len(self.max_raises_by_hand) + PRIOR_HANDS)


# ---------------------------------------------------------------------------
# Per-match counts of what the opponent does (#158). Counting only: nothing reads them.

OUTCOMES = {"first_in": ("fold", "limp", "raise", "shove", "other"),
            "vs_open": ("fold", "call", "raise", "shove", "other"),
            "vs_shove": ("fold", "call", "other"),
            "cbet": ("check", "bet", "other"),
            "checked_to": ("check", "bet", "other"),
            "vs_bet": ("fold", "call", "raise", "other")}
_BUCKETS = ("le10", "10to20", "deep", "na")
_ACTIONS = ("fold", "check", "call", "raise", "all_in")
_AGG = ("raise", "all_in")
# summary key order: (base, suffixes)
_ORDER = (("first_in", _BUCKETS), ("vs_open", _BUCKETS), ("vs_shove", _BUCKETS),
          ("cbet", ("",)), ("checked_to", ("",)), ("vs_bet", ("1", "2", "3")))


def parse_actions(action_history, our_seat):
    """The one place that reads a history: voluntary entries only (blind and ante posts dropped), labels
    normalised (a bench "bet" is a "raise"). Returns (is_opponent, label, amount, phase) in order."""
    out = []
    for e in action_history or ():
        a = e.get("action")
        if isinstance(a, str) and (a.startswith("post_") or a == "ante"):
            continue
        out.append((e.get("seat") != our_seat, "raise" if a == "bet" else a, e.get("amount"), e.get("phase")))
    return out


class OpponentStats:
    """counts[key][outcome] = n, one object per match. observe_hand never raises; errors counts the failures."""

    def __init__(self):
        self.counts, self.hands, self.errors = {}, 0, 0

    def observe_hand(self, action_history, our_seat, eff=None, depth_bb=None):
        self.hands += 1
        try:
            events = self._classify(action_history, our_seat, eff, depth_bb)
        except Exception:
            self.errors += 1
            return
        for key, out in events:  # applied only once the whole hand parsed
            self.counts.setdefault(key, {o: 0 for o in OUTCOMES[key.split("@")[0]]})[out] += 1

    @staticmethod
    def _classify(history, our, eff, depth_bb):
        if any(not isinstance(e["seat"], int) for e in history):
            raise ValueError("entry without a seat")
        es, seen, last = [], [], None  # seen: amounts of aggressive entries on this street
        for opp, a, amt, ph in parse_actions(history, our):
            if a not in _ACTIONS:
                continue
            amt = int(amt or 0)
            # An all_in is a call when an earlier aggressive entry on its street (either seat) is at least as big.
            if ph != last:
                seen, last = [], ph
            if a == "all_in" and any(x >= amt for x in seen):
                a = "call"
            elif a in _AGG:
                seen.append(amt)
            es.append((opp, a, amt, ph))

        agg = lambda e: e[1] in _AGG
        shove = lambda e: agg(e) and (e[1] == "all_in" or (eff is not None and e[2] >= eff))
        bucket = ("na" if depth_bb is None else "le10" if depth_bb <= 10 else "10to20" if depth_bb <= 20 else "deep")
        ev = []

        def add(key, e, sh=False):
            kind, a = key.split("@")[0], e[1]
            if a in ("fold", "check"):
                out = a
            elif a == "call":
                out = "limp" if kind == "first_in" else "call"
            elif kind in ("first_in", "vs_open"):
                out = "shove" if sh else "raise"
            else:
                out = {"vs_bet": "raise", "vs_shove": "call"}.get(kind, "bet")
            ev.append((key, out if out in OUTCOMES[kind] else "other"))

        pre = [e for e in es if e[3] == "preflop"]
        streets, last = [], None  # a new street at each change of phase
        for e in es:
            if e[3] != "preflop":
                if e[3] != last:
                    streets.append([])
                    last = e[3]
                streets[-1].append(e)

        if pre:
            if pre[0][0]:
                add("first_in@" + bucket, pre[0], shove(pre[0]))
            elif agg(pre[0]) and not shove(pre[0]):
                nxt = next((e for e in pre[1:] if e[0]), None)
                if nxt:
                    add("vs_open@" + bucket, nxt, shove(nxt))
        for i, e in enumerate(pre):
            if not e[0] and shove(e):
                nxt = next((x for x in pre[i + 1:] if x[0]), None)
                if nxt:
                    add("vs_shove@" + bucket, nxt)

        aggressors = [e[0] for e in pre if agg(e)]
        if streets and aggressors and aggressors[-1]:  # the opponent was the last preflop aggressor
            for j, e in enumerate(streets[0]):
                if e[0]:
                    if not any(agg(x) for x in streets[0][:j]):
                        add("cbet", e)
                    break

        for n, street in enumerate(streets, 1):
            for i, e in enumerate(street):
                if not e[0] and agg(e):
                    nxt = next((x for x in street[i + 1:] if x[0]), None)
                    if nxt:
                        add("vs_bet@%d" % n, nxt)
                if e[0] and i > 0 and not street[i - 1][0] and street[i - 1][1] == "check" \
                        and not any(agg(x) for x in street[:i]):
                    add("checked_to", e)
        return ev

    def summary(self):
        """hands=<h> errors=<e> then each key with n>0 as key=n:o1/o2/..., in a fixed order."""
        parts = ["hands=%d" % self.hands, "errors=%d" % self.errors]
        for base, sufs in _ORDER:
            for s in sufs:
                key = base + "@" + s if s else base
                c = self.counts.get(key)
                if c and sum(c.values()):
                    parts.append("%s=%d:%s" % (key, sum(c.values()), "/".join(str(c[o]) for o in OUTCOMES[base])))
        return " ".join(parts)
