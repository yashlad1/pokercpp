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
(Filled in after the runs.)
