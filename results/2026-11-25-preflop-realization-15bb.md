# Preflop realization at 15 bb (#81, #97)

Date: 2026-11-25. Parent: #52. The design below was committed before any variant was run.

## Question
In live match 1, 28 of 30 preflop folds faced a 6.2 bb open. Does a smaller preflop realization discount, which calls more of those opens, win more against aggro at 15 bb without losing against reference?

## Design
- **Build:** one build, `engine/preflop-realization` (#97). The variants differ only in the runtime flag `--preflop-realization`. Flop, turn and river discounts are unchanged.
- **Variants:** 0.75 (shipping, the baseline), 0.85, 0.95.
- **Opponents:** aggro (the test), reference (the control).
- **Runs:** engine hero, 2000 sims, `--stack 15`, `--hands 4000` (2000 seat-swapped pairs), seed0 700001 and 710001.
- **Comparison:** `tools/paired.py` on the `--dump` files, variant minus baseline, in bb/100 with its 95% interval.
- **Adoption rule:** a value is adopted only if, on both seed sets, (1) its paired gain against aggro has a 95% interval entirely above 0, and (2) its paired point estimate against reference is not below 0. If both values pass, take 0.85 unless 0.95's gain against aggro is larger on both seed sets. Otherwise the change is parked with these numbers.
- **Scope:** "adopted" means recommended. Changing the live bot is a separate decision.

## Commands
    PYTHONPATH=chipzen python tools/bench.py --hero engine --sims 2000 --stack 15 --hands 4000 \
        --vs <aggro|reference> --seed0 <700001|710001> [--preflop-realization <0.85|0.95>] --dump <file>
    python tools/paired.py <baseline.json> <variant.json>

## Results
Gain is variant minus 0.75 on the same deals. `tools/paired.py` prints baseline minus variant, so its sign is flipped here.

| Opponent | Seed | Variant | bb/100 [95% CI] | Gain vs 0.75, bb/100 [95% CI] |
|---|---|---|---|---|
| aggro | 700001 | 0.75 | +19.4 [-2.1, +40.8] | baseline |
| aggro | 700001 | 0.85 | +43.4 [+20.3, +66.6] | +24.1 [+7.7, +40.5] |
| aggro | 700001 | 0.95 | +49.4 [+27.3, +71.6] | +30.1 [+9.2, +51.0] |
| aggro | 710001 | 0.75 | +14.4 [-7.5, +36.4] | baseline |
| aggro | 710001 | 0.85 | +52.0 [+29.2, +74.8] | +37.5 [+20.7, +54.4] |
| aggro | 710001 | 0.95 | +47.7 [+25.3, +70.0] | +33.2 [+12.4, +54.1] |
| reference | 700001 | 0.75 | +53.9 [+50.1, +57.8] | baseline |
| reference | 700001 | 0.85 | +54.6 [+50.2, +59.0] | +0.7 [-1.5, +2.9] |
| reference | 700001 | 0.95 | +54.4 [+49.8, +59.1] | +0.5 [-2.3, +3.4] |
| reference | 710001 | 0.75 | +54.1 [+50.3, +57.9] | baseline |
| reference | 710001 | 0.85 | +54.7 [+50.5, +59.0] | +0.6 [-1.3, +2.6] |
| reference | 710001 | 0.95 | +56.2 [+51.6, +60.7] | +2.1 [-0.7, +4.8] |

**Verdict:** 0.85 and 0.95 both pass the rule (aggro gain interval above 0 on both seed sets; reference gain at or above 0 on both). 0.95's aggro gain is larger on seed 700001 (+30.1 against +24.1) but not on 710001 (+33.2 against +37.5), so the tie-break picks 0.85: **adopted 0.85** (recommended only; the live bot is unchanged).

Run time: each run took 14 to 20 seconds, with 8 to 12 runs going in parallel.
