# Verbatim copy of the Stats class (chipzen/opponent.py) at commit 47fcb67, used for the opponent counts.
"""Per-match memory of how often the opponent raises.

The engine reads a hand's own raises as a range: one raise is the top 45%,
three the top 8%. That is wrong for an opponent who raises every hand, whose
third raise is no stronger than their first. This remembers the match so far
so the engine can widen its guess for such an opponent.
"""

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
        self.raises = {}  # hand id -> most raises villain made in it, as seen at our turns

    def saw(self, hand, villain_raises):
        self.raises[hand] = max(self.raises.get(hand, 0), villain_raises)

    def range_floor(self, villain_raises):
        """Fraction of hands in which villain made at least this many raises."""
        if villain_raises < 1:
            return 0.0
        hits = sum(r >= villain_raises for r in self.raises.values())
        return hits / (len(self.raises) + PRIOR_HANDS)


class Stats:
    """Counts what villain does in each situation: counts[key][outcome] = n.

    Counting only. Nothing reads these yet.
    """

    OUTCOMES = {"first_in": ("fold", "limp", "raise", "shove", "other"),
                "vs_open": ("fold", "call", "raise", "shove", "other"),
                "vs_shove": ("fold", "call", "other"),
                "cbet": ("check", "bet", "other"),
                "checked_to": ("check", "bet", "other"),
                "vs_bet": ("fold", "call", "raise", "other")}
    ACTIONS = ("fold", "check", "call", "raise", "bet", "all_in")

    def __init__(self):
        self.counts = {}

    def _add(self, key, e, shove=False):
        kind = key.split("@")[0]
        a = e["action"]
        if a in ("fold", "check"):
            out = a
        elif a == "call":
            out = "limp" if kind == "first_in" else "call"
        elif kind in ("first_in", "vs_open"):
            out = "shove" if shove else "raise"
        else:
            out = {"vs_bet": "raise", "vs_shove": "call"}.get(kind, "bet")
        if out not in self.OUTCOMES[kind]:
            out = "other"
        self.counts.setdefault(key, {o: 0 for o in self.OUTCOMES[kind]})[out] += 1

    def record_hand(self, history, our_seat, depth_bb=None, eff=None):
        try:
            self._record(history, our_seat, depth_bb, eff)
        except Exception:
            pass

    def _record(self, history, our_seat, depth_bb, eff):
        entries = [e for e in history
                   if isinstance(e, dict) and "seat" in e and "action" in e and "phase" in e
                   and e["action"] in self.ACTIONS]

        def num(x):
            return isinstance(x, (int, float)) and not isinstance(x, bool)

        # An all_in is a call, not aggression, when an earlier aggressive entry on the
        # same street (either seat) has an amount at least as big. Judged in order, so
        # earlier entries already carry this rule.
        # ponytail: an all_in with no usable amount still counts as aggressive.
        seen, last, fixed = [], None, []  # seen: amounts of aggressive entries this street
        for e in entries:
            if e["phase"] != last:
                seen, last = [], e["phase"]
            if e["action"] == "all_in" and num(e.get("amount")) and any(a >= e["amount"] for a in seen):
                e = dict(e, action="call")
            elif e["action"] in ("raise", "bet", "all_in") and num(e.get("amount")):
                seen.append(e["amount"])
            fixed.append(e)
        entries = fixed

        def agg(e):
            return e["action"] in ("raise", "bet", "all_in")

        def vil(e):
            return e["seat"] != our_seat

        def shove(e):
            amt = e.get("amount")
            return agg(e) and (e["action"] == "all_in" or (eff is not None and num(amt) and amt >= eff))

        bucket = ("na" if depth_bb is None else "le10" if depth_bb <= 10
                  else "10to20" if depth_bb <= 20 else "deep")
        pre = [e for e in entries if e["phase"] == "preflop"]
        streets, last = [], None  # postflop: a new street at each change of phase value
        for e in entries:
            if e["phase"] == "preflop":
                continue
            if e["phase"] != last:
                streets.append([])
                last = e["phase"]
            streets[-1].append(e)

        if pre:
            if vil(pre[0]):
                self._add("first_in@" + bucket, pre[0], shove(pre[0]))
            elif agg(pre[0]) and not shove(pre[0]):
                nxt = next((e for e in pre[1:] if vil(e)), None)
                if nxt:
                    self._add("vs_open@" + bucket, nxt, shove(nxt))
        for i, e in enumerate(pre):
            if not vil(e) and shove(e):
                nxt = next((x for x in pre[i + 1:] if vil(x)), None)
                if nxt:
                    self._add("vs_shove@" + bucket, nxt)

        aggressors = [e["seat"] for e in pre if agg(e)]
        if streets and aggressors and aggressors[-1] != our_seat:
            flop = streets[0]
            for j, e in enumerate(flop):
                if vil(e):
                    if not any(agg(x) for x in flop[:j]):
                        self._add("cbet", e)
                    break

        for n, street in enumerate(streets, 1):
            for i, e in enumerate(street):
                if not vil(e) and agg(e):
                    nxt = next((x for x in street[i + 1:] if vil(x)), None)
                    if nxt:
                        self._add(f"vs_bet@{n}", nxt)
                if (vil(e) and i > 0 and not vil(street[i - 1]) and street[i - 1]["action"] == "check"
                        and not any(agg(x) for x in street[:i])):
                    self._add("checked_to", e)
