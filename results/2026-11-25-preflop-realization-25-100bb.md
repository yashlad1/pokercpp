# Preflop realization at 25 and 100 bb (#82)

Date: 2026-11-25. Parent: #52. The design below was committed before any run. It repeats #81 (results/2026-11-25-preflop-realization-15bb.md) at two more depths.

## Design
- **Build, variants, opponents, runs, comparison:** as in #81. One build (#97); 0.75 (baseline), 0.85, 0.95; aggro (test) and reference (control); engine hero, 2000 sims, `--hands 4000` (2000 seat-swapped pairs), seed0 700001 and 710001, `tools/paired.py`, variant minus baseline.
- **Depths:** `--stack 25` and `--stack 100`.
- **Adoption rule, applied per depth:** as in #81. A value is adopted at a depth only if, on both seed sets, its paired gain against aggro has a 95% interval entirely above 0 and its paired point estimate against reference is not below 0. If both values pass, take 0.85 unless 0.95's gain against aggro is larger on both seed sets.
- **Extra check (not part of the rule):** 0.85 against 0.75 at 15 bb against every other opponent registered in `tools/bench.py`, on both seed sets. Any opponent where the 0.85 gain interval lies entirely below 0 is flagged. This informs the ship decision only.

## Results
(Filled in after the runs.)
