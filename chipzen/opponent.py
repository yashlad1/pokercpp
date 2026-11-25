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

# ponytail: all fitted, not measured. Showdown bluff estimate: the balanced
# bluff share at a half-pot bet is the prior, the ramp and gate keep a few
# hands from moving it, and the scale caps at doubling the assumed range.
# Only ever widens. STEP mirrors villainRangeFraction in decide.h.
BLUFF_PRIOR = 0.25
BLUFF_PRIOR_N = 6.0
BLUFF_MIN_N = 3
BLUFF_RAMP_N = 10
BLUFF_MAX_SCALE = 2.0
STEP = {1: 0.45, 2: 0.18, 3: 0.08}


class Opponent:
    """Counts, per hand, the most raises villain made as seen at our turns."""

    def __init__(self):
        self.raises = {}  # hand id -> most raises villain made in it, as seen at our turns
        self.n = self.k = 0  # shown postflop bets, and how many were air
        self._hands = set()  # hand numbers already learned from

    def saw(self, hand, villain_raises):
        self.raises[hand] = max(self.raises.get(hand, 0), villain_raises)

    def learn(self, result, my_seat):
        """Count one hand's showdown: a postflop bet shown down as air or not."""
        try:
            hand = result.get("hand_number")  # 0 or None: nothing to dedupe on
            if hand and hand in self._hands:
                return
            opp = [e for e in result["showdown"] if e["seat"] != my_seat]
            if len(opp) != 1:  # our seat unknown or not in this showdown
                return
            opp = opp[0]
            if not any(e["seat"] == opp["seat"] and e["action"] == "raise"
                       and e["phase"] in ("flop", "turn", "river")
                       for e in result["action_history"]):
                return
            rank = opp["hand_rank"]
            holes = {c[0] for c in opp["hole_cards"]}
            ranks = [c[0] for c in opp["best_hand"]]
            air = rank == "High Card" or (
                rank == "Pair" and not any(r in holes and ranks.count(r) == 2 for r in ranks))
            if hand:
                self._hands.add(hand)
            self.n += 1
            self.k += air
        except Exception:
            pass

    def bluff(self):
        """(estimated bluff share b, range scale >= 1) from the shown bets so far."""
        b = (self.k + BLUFF_PRIOR * BLUFF_PRIOR_N) / (self.n + BLUFF_PRIOR_N)
        if self.n < BLUFF_MIN_N or b <= BLUFF_PRIOR:
            return b, 1.0
        b_eff = BLUFF_PRIOR + min(1, self.n / BLUFF_RAMP_N) * (b - BLUFF_PRIOR)
        return b, min(BLUFF_MAX_SCALE, (1 - BLUFF_PRIOR) / (1 - b_eff))

    def range_floor(self, villain_raises):
        """Fraction of hands in which villain made at least this many raises."""
        if villain_raises < 1:
            return 0.0
        hits = sum(r >= villain_raises for r in self.raises.values())
        floor = hits / (len(self.raises) + PRIOR_HANDS)
        scale = self.bluff()[1]
        if scale > 1:
            floor = max(floor, min(1.0, STEP[min(villain_raises, 3)] * scale))
        return floor
