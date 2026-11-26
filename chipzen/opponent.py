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
        self.raises = {}  # hand id -> most raises villain made in it, as seen at our turns

    def saw(self, hand, villain_raises):
        self.raises[hand] = max(self.raises.get(hand, 0), villain_raises)

    def range_floor(self, villain_raises):
        """Fraction of hands in which villain made at least this many raises."""
        if villain_raises < 1:
            return 0.0
        hits = sum(r >= villain_raises for r in self.raises.values())
        return hits / (len(self.raises) + PRIOR_HANDS)
