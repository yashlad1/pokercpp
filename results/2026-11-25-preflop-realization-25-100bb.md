# Preflop realization at 25 and 100 bb (#82)

Date: 2026-11-25. Parent: #52. The design below was committed before any run. It repeats #81 (results/2026-11-25-preflop-realization-15bb.md) at two more depths.

## Design
- **Build, variants, opponents, runs, comparison:** as in #81. One build (#97); 0.75 (baseline), 0.85, 0.95; aggro (test) and reference (control); engine hero, 2000 sims, `--hands 4000` (2000 seat-swapped pairs), seed0 700001 and 710001, `tools/paired.py`, variant minus baseline.
- **Depths:** `--stack 25` and `--stack 100`.
- **Adoption rule, applied per depth:** as in #81. A value is adopted at a depth only if, on both seed sets, its paired gain against aggro has a 95% interval entirely above 0 and its paired point estimate against reference is not below 0. If both values pass, take 0.85 unless 0.95's gain against aggro is larger on both seed sets.
- **Extra check (not part of the rule):** 0.85 against 0.75 at 15 bb against every other opponent registered in `tools/bench.py`, on both seed sets. Any opponent where the 0.85 gain interval lies entirely below 0 is flagged. This informs the ship decision only.

## Results
Gain is variant minus 0.75 on the same deals. `tools/paired.py` prints baseline minus variant, so its sign is flipped here.

### 25 bb

| Opponent | Seed | Variant | bb/100 [95% CI] | Gain vs 0.75 [95% CI] |
|---|---|---|---|---|
| aggro | 700001 | 0.75 | +47.3 [+13.0, +81.5] | baseline |
| aggro | 700001 | 0.85 | +100.0 [+62.6, +137.4] | +52.8 [+25.8, +79.7] |
| aggro | 700001 | 0.95 | +101.5 [+63.6, +139.5] | +54.3 [+21.2, +87.4] |
| aggro | 710001 | 0.75 | +46.4 [+11.5, +81.3] | baseline |
| aggro | 710001 | 0.85 | +107.7 [+70.1, +145.3] | +61.3 [+33.5, +89.1] |
| aggro | 710001 | 0.95 | +115.4 [+77.5, +153.2] | +69.0 [+34.9, +103.1] |
| reference | 700001 | 0.75 | +51.7 [+46.5, +56.8] | baseline |
| reference | 700001 | 0.85 | +52.9 [+47.2, +58.6] | +1.2 [-1.3, +3.7] |
| reference | 700001 | 0.95 | +53.4 [+47.5, +59.2] | +1.7 [-1.6, +5.0] |
| reference | 710001 | 0.75 | +50.7 [+45.7, +55.8] | baseline |
| reference | 710001 | 0.85 | +51.7 [+46.3, +57.2] | +1.0 [-1.0, +3.0] |
| reference | 710001 | 0.95 | +53.0 [+47.2, +58.9] | +2.3 [-0.8, +5.3] |

**Verdict (25 bb):** both values pass the rule (aggro gain intervals above 0 and reference point estimates at or above 0, on both seed sets). 0.95's aggro gain is larger on both seed sets (+54.3 against +52.8, +69.0 against +61.3), so **adopted 0.95** at 25 bb (recommended only).

### 100 bb

| Opponent | Seed | Variant | bb/100 [95% CI] | Gain vs 0.75 [95% CI] |
|---|---|---|---|---|
| aggro | 700001 | 0.75 | +587.0 [+472.0, +702.0] | baseline |
| aggro | 700001 | 0.85 | +775.2 [+648.6, +901.8] | +188.2 [+100.9, +275.6] |
| aggro | 700001 | 0.95 | +872.1 [+739.1, +1005.2] | +285.2 [+174.7, +395.6] |
| aggro | 710001 | 0.75 | +629.6 [+514.5, +744.6] | baseline |
| aggro | 710001 | 0.85 | +835.7 [+703.7, +967.7] | +206.2 [+113.7, +298.6] |
| aggro | 710001 | 0.95 | +910.7 [+773.4, +1047.9] | +281.1 [+166.7, +395.5] |
| reference | 700001 | 0.75 | +53.1 [+45.9, +60.3] | baseline |
| reference | 700001 | 0.85 | +54.1 [+45.9, +62.2] | +1.0 [-2.9, +4.9] |
| reference | 700001 | 0.95 | +58.7 [+49.2, +68.1] | +5.5 [-1.8, +12.8] |
| reference | 710001 | 0.75 | +53.1 [+44.6, +61.5] | baseline |
| reference | 710001 | 0.85 | +53.9 [+45.2, +62.6] | +0.8 [-1.4, +3.1] |
| reference | 710001 | 0.95 | +54.3 [+44.3, +64.3] | +1.2 [-5.2, +7.6] |

**Verdict (100 bb):** both values pass the rule. 0.95's aggro gain is larger on both seed sets (+285.2 against +188.2, +281.1 against +206.2), so **adopted 0.95** at 100 bb (recommended only).

### Other opponents, 0.85 against 0.75 at 15 bb

| Opponent | Seed | 0.75 bb/100 | 0.85 bb/100 | Gain [95% CI] | Flagged |
|---|---|---|---|---|---|
| station | 700001 | +177.0 | +176.1 | -0.8 [-2.3, +0.6] | no |
| station | 710001 | +197.6 | +198.0 | +0.4 [-1.5, +2.3] | no |
| nit | 700001 | +54.3 | +54.8 | +0.5 [-2.3, +3.2] | no |
| nit | 710001 | +56.2 | +58.0 | +1.8 [-0.9, +4.6] | no |
| maniac | 700001 | +80.9 | +84.5 | +3.6 [-4.4, +11.6] | no |
| maniac | 710001 | +69.8 | +66.0 | -3.8 [-10.8, +3.2] | no |
| switcher | 700001 | +64.6 | +67.7 | +3.1 [-13.9, +20.1] | no |
| switcher | 710001 | +59.2 | +51.4 | -7.8 [-25.6, +10.1] | no |
| loosepassive | 700001 | +177.0 | +176.1 | -0.8 [-2.3, +0.6] | no |
| loosepassive | 710001 | +197.6 | +198.0 | +0.4 [-1.5, +2.3] | no |
| random | 700001 | +77.0 | +86.2 | +9.2 [-0.0, +18.4] | no |
| random | 710001 | +76.9 | +93.4 | +16.5 [+7.6, +25.4] | no |
| bluff0 | 700001 | +53.9 | +54.6 | +0.7 [-1.5, +2.9] | no |
| bluff0 | 710001 | +54.1 | +54.7 | +0.6 [-1.3, +2.6] | no |
| bluff25 | 700001 | +52.0 | +52.2 | +0.3 [-2.0, +2.5] | no |
| bluff25 | 710001 | +52.2 | +52.6 | +0.4 [-1.6, +2.5] | no |
| bluff50 | 700001 | +50.5 | +50.8 | +0.3 [-2.0, +2.7] | no |
| bluff50 | 710001 | +49.5 | +49.9 | +0.3 [-1.8, +2.4] | no |
| loosebluff0 | 700001 | +27.8 | +33.9 | +6.0 [+3.1, +8.9] | no |
| loosebluff0 | 710001 | +31.7 | +37.7 | +6.0 [+3.2, +8.8] | no |
| loosebluff25 | 700001 | +25.2 | +32.0 | +6.8 [+3.4, +10.2] | no |
| loosebluff25 | 710001 | +31.8 | +40.1 | +8.3 [+4.5, +12.0] | no |
| loosebluff50 | 700001 | +25.2 | +28.8 | +3.6 [+0.2, +7.0] | no |
| loosebluff50 | 710001 | +33.6 | +40.3 | +6.7 [+2.6, +10.7] | no |

**Flags:** none. No opponent has a 0.85 gain interval entirely below 0. The largest gains are against random on 710001 (+16.5 [+7.6, +25.4]) and the loosebluff opponents (+3.6 to +8.3, intervals above 0 on all six). Station and loosepassive give identical numbers.

Run time: each run took 13 to 70 seconds, with 8 running in parallel. Eval log rows R202-R217 (25 and 100 bb) and R218-R241 (other opponents).
