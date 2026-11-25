# Bluff detector gate (24 Nov 2026)

**Question:** does the in-match bluff detector (draft PR #56, branch `research/bluff-detect`, 980748b, issue #51) change play against bluffers, and does it hurt against anyone else?

**Method:** ON is that branch. OFF is the same code with `BLUFF_MAX_SCALE = 1.0`, which makes the range widening a no-op. Identical bench code otherwise.
- `--hero bot`, 2000 hands (1000 seat-swapped pairs) per row, 2000 sims, at 15 and 100 bb.
- Fresh seed sets 720001 and 730001. Opponents: loosebluff25, loosebluff50, reference, nit, loosebluff0, switcher (24 rows).
- Match mode: 400 matches per row (200 seeds, both seats), same 12 seed/opponent cells, ON and OFF.

**Decision rule, fixed before the runs:**
- Fail = the ON-minus-OFF interval is entirely below 0. It blocks only if it fails on both seed sets.
- Pass = no blocking fail on the controls, and a loose bluffer above 0 on both seed sets.

**Sanity check:** ON and OFF `--dump` output against reference (300 hands, 300 sims, 100 bb, seed0 3) is byte-identical.

## Paired chips, ON minus OFF (bb/100, 95% interval)

| Depth | Seed0 | Opponent | ON - OFF |
|---|---|---|---|
| 15 bb | 720001 | loosebluff50 | -0.7 [-1.5, +0.2] |
| 100 bb | 720001 | loosebluff50 | -3.2 [-10.4, +4.1] |
| 100 bb | 720001 | nit | +4.2 [-6.0, +14.4] |
| 15 bb | 730001 | loosebluff50 | +4.1 [-2.2, +10.3] |
| 100 bb | 730001 | loosebluff25 | +0.4 [-0.4, +1.2] |
| 100 bb | 730001 | loosebluff50 | +2.4 [-5.5, +10.2] |

Every other row (18 of 24) was exactly +0.0 [+0.0, +0.0]. No interval is above or below 0. The nit row differs although the match-mode runs never saw scale > 1 against nit; its cause was not checked.

## Detector activity (ON, seed 720001)

| Opponent | Depth | n (showdowns) | k (air) | b (estimate) | Final scale | Max scale | Calls with scale > 1 |
|---|---|---|---|---|---|---|---|
| loosebluff25 | 15 bb | 65 | 12 | 0.190 | 1.000 | 1.000 | 0 |
| loosebluff25 | 100 bb | 71 | 15 | 0.214 | 1.000 | 1.000 | 0 |
| loosebluff50 | 15 bb | 86 | 22 | 0.255 | 1.007 | 1.119 | 1223 |
| loosebluff50 | 100 bb | 92 | 29 | 0.311 | 1.089 | 1.143 | 1890 |

## Match mode (400 matches per row)

| Seed0 | Opponent | ON win rate | OFF win rate | ON won, OFF lost | ON lost, OFF won | Matches with scale > 1 |
|---|---|---|---|---|---|---|
| 720001 | loosebluff25 | 339/400 = 84.8% [80.9, 87.9] | 340/400 = 85.0% [81.2, 88.2] | 15 | 16 | 100/400 (25%) |
| 720001 | loosebluff50 | 308/400 = 77.0% [72.6, 80.9] | 308/400 = 77.0% [72.6, 80.9] | 18 | 18 | 179/400 (45%) |
| 720001 | reference | 397/400 = 99.2% [97.8, 99.7] | 397/400 = 99.2% [97.8, 99.7] | 0 | 0 | 0/400 |
| 720001 | nit | 400/400 = 100.0% [99.0, 100.0] | 400/400 = 100.0% [99.0, 100.0] | 0 | 0 | 0/400 |
| 720001 | loosebluff0 | 350/400 = 87.5% [83.9, 90.4] | 350/400 = 87.5% [83.9, 90.4] | 0 | 0 | 0/400 |
| 720001 | switcher | 279/400 = 69.8% [65.1, 74.0] | 279/400 = 69.8% [65.1, 74.0] | 0 | 0 | 0/400 |
| 730001 | loosebluff25 | 324/400 = 81.0% [76.9, 84.5] | 323/400 = 80.8% [76.6, 84.3] | 17 | 16 | 95/400 (24%) |
| 730001 | loosebluff50 | 313/400 = 78.2% [73.9, 82.0] | 310/400 = 77.5% [73.2, 81.3] | 13 | 10 | 177/400 (44%) |
| 730001 | reference | 398/400 = 99.5% [98.2, 99.9] | 398/400 = 99.5% [98.2, 99.9] | 0 | 0 | 0/400 |
| 730001 | nit | 399/400 = 99.8% [98.6, 100.0] | 399/400 = 99.8% [98.6, 100.0] | 0 | 0 | 0/400 |
| 730001 | loosebluff0 | 347/400 = 86.8% [83.1, 89.7] | 347/400 = 86.8% [83.1, 89.7] | 0 | 0 | 0/400 |
| 730001 | switcher | 257/400 = 64.2% [59.4, 68.8] | 257/400 = 64.2% [59.4, 68.8] | 0 | 0 | 0/400 |

## Verdict: inconclusive

No blocking fail, but no loose bluffer is above 0 on both seed sets, so the pass condition is not met.
- **Loosebluff25:** the detector never fires in the activity runs. Its estimate stays at or below the 0.25 prior (0.19 and 0.21), so scale stays 1.0. Nothing to measure.
- **Loosebluff50:** scale peaks at only 1.12 to 1.14, though the true bluff rate is higher. Bluffs we fold to never reach showdown, so the air count undercounts them. This is the censoring the research warned about.
- **Controls:** play is unchanged against reference, loosebluff0, switcher, and (in match mode) nit. The detector is safe but mostly inactive.
- **Where it differs:** only loosebluff50 and loosebluff25 (100 bb) move chips, all within noise.

## Wall times

- Paired chips: 48 runs (24 rows, ON and OFF), 11 s at most each and about 8 s on average, about 100 s in total for each depth.
- Activity: about 40 s.
- Match mode: about 2,575 CPU-s in total (about 11 min with 4 in parallel).
