# Metal vs CPU parity (2026-11-25)

Issue #38. Compares a plain CPU build of the engine with a `-DUSE_METAL` build (Apple Silicon, M4). Run with `python tools/metal_parity.py`. On a machine with no Metal build it prints "Metal not available" and exits 0, so CI on Linux skips it.

## Method

- **Builds.** `tools/build_engine.sh` and `tools/build_engine.sh --metal`, each copied to its own directory. The module name is the same, so the script runs each build in its own process.
- **Decision parity.** 1,000 seeded random spots (preflop, flop, turn and river; stacks of 8, 15, 30 and 100 bb; checked-to and facing a bet; 0 to 2 villain raises), 20,000 sims, a fixed engine seed per spot. Both builds return the action plus equity, realized and required.
- **Explaining a disagreement.** The decision gates are equity against 0.30, 0.50, 0.55, 0.62 and 0.75, and realized against required. A disagreement is explained when the nearest of those is within 4 standard errors of a difference of two 20,000-sim estimates (0.020 equity).
- **Control.** The CPU build again on the same spots with different engine seeds. It gives the flip rate of one implementation against itself on this mix.
- **Bench parity.** `tools/bench.py` duplicate-dealt matches, hero `PokerCpp` at 2,000 sims, once per build, same deal seeds, 60,000 hands each, run as 8 processes per build (each process starts with fresh opponent memory; both builds are split the same way). Interval is on the per-pair difference, as in `tools/paired.py`.
- **Pass rule (pre-registered).** Fixed in the commit before the fresh-seed run below; the first run's rule was changed after seeing its data, so this one is written down first. Parity passes only if all four hold: (a) flips <= control + 2 SD, or more than 99% the same action; (b) every disagreement is within the noise band; (c) the mean of d = metal equity minus CPU equity per spot is within 4 SE of 0 (SE = stdev(d)/sqrt(n)), overall and on each street (preflop, flop, turn, river); (d) each bench interval contains 0. Local only, never in CI; exits 0 when no Metal build exists.

## First run (rule changed after seeing the data)

The tables below are the PR's first run: spot seed 38, 60,000 hands per opponent. Its flip-count rule was adopted after the 98.6% result, so it counts as exploratory. The confirmation is the fresh-seed run further down, under the rule above.

## Decision parity

| Check | Result |
|---|---|
| Same action, Metal vs CPU | 98.6% (986 of 1,000) |
| Disagreements | 14 (1.4%) |
| Control, CPU vs CPU, other seeds | 10 disagreements (1.0%) |
| Disagreements within noise of a threshold | 14 of 14 |

Largest distance from a threshold among the 14: 0.0024 equity, against a band of 0.020. The two equities in each pair differ by 0.001 to 0.008. Nine sit at the 0.50, 0.55, 0.62 or 0.75 cuts and five at the call gate (realized vs required).

**The 99% bar.** The issue asks for more than 99%. This mix misses it, and so does CPU against itself (the control flipped 10 times, Metal 14; 10 flips is exactly 99.0%, and 14 against 10 is within count noise). The mix is deliberately dense near thresholds, so the share depends on the mix more than on the build. The script therefore treats "no more than the control" as the pass; the strict 99% reading is not met here.

## Bench parity (paired, same seeds)

| Opponent | Hands | CPU hero | Metal hero | Metal minus CPU, bb/100 (95% interval) |
|---|---|---|---|---|
| Reference, 15 bb | 60,000 | +54.1 | +54.0 | -0.2 [-0.6, +0.2] |
| Aggro, 100 bb | 60,000 | +499.0 | +506.4 | +7.3 [-4.3, +19.0] |

Both intervals contain 0.

**Aggro is noisy.** Its per-hand spread is large, so an interval is wide and a fixed-seed run misses 0 about one time in twenty. Earlier runs on other seed sets gave: 6,000 hands +49.9 [+11.5, +88.3] (excluded 0), 12,000 hands -3.2 [-28.0, +21.6], 12,000 hands +11.1 [-15.2, +37.5], 20,000 hands +21.5 [+2.4, +40.7] (excluded 0, overlaps the first set), and a fresh 60,000 hands -3.0 [-14.7, +8.7]. The sign flips across independent sets, which is what chance looks like, but a small Metal edge vs aggro (a few bb/100 on about +500) is not ruled out.

## Fresh-seed confirmation (pre-registered rule)

Run under the rule above, which was committed before this run. Spot seed 3801, engine seed offset 500000 (control at 600000), bench seed0 500001, 20,000 hands per opponent per build, default opponents. Seeds are new; nothing was tuned.

| Check | Result |
|---|---|
| Same action, Metal vs CPU | 99.4% (994 of 1,000), 6 flips |
| Control, CPU vs CPU, other seeds | 8 flips; limit 13.7 (control + 2 SD) |
| Disagreements within noise of a threshold | 6 of 6 (largest distance 0.0023 equity, band 0.020) |
| Equity mean difference, all spots | +0.00007 (SE 0.00013, 0.5 SE) |
| Preflop, n=247 | -0.00038 (SE 0.00030, 1.2 SE) |
| Flop, n=263 | +0.00020 (SE 0.00026, 0.8 SE) |
| Turn, n=236 | +0.00015 (SE 0.00025, 0.6 SE) |
| River, n=254 | +0.00028 (SE 0.00025, 1.1 SE) |

| Opponent | Hands | CPU hero | Metal hero | Metal minus CPU, bb/100 (95% interval) |
|---|---|---|---|---|
| Reference, 15 bb | 19,992 | +53.9 | +53.9 | -0.0 [-0.7, +0.6] |
| Aggro, 100 bb | 19,992 | +502.9 | +500.3 | -2.6 [-21.8, +16.6] |

Verdict: **PARITY HOLDS**, exit code 0. All four conditions hold, and this run also clears the issue's 99% bar (99.4%). The aggro interval is wide (about +/-19 bb/100), so a small Metal edge vs aggro is still not ruled out; it is not seen.

## Detection check (scratch Metal builds, not committed)

A constant added to the equity the Metal path returns, decision part only, default spots (spot seed 38, no engine seed offset).

| Mutant | Same action | Flip rule (a) | Mean difference (c) | Exit |
|---|---|---|---|---|
| +0.03 | 93.5%, 65 flips vs control 10 (limit 16.3) | fails | +0.02994, 225.7 SE overall, 104 to 141 SE per street | 1 |
| +0.002 | 98.9%, 11 flips vs control 10 (limit 16.3) | passes | +0.00194, 14.6 SE overall, 5.8 to 9.6 SE per street | 1 |

The +0.002 shift is invisible to the flip rule: the flip count stays inside the control's range. Only the mean-difference check catches it, which is why it was added. The first run's 98.6% was checked the same way after the fact only for the flip count; the mean-difference check was not in that run.

## Not done from the issue

- The linux/amd64 image against the Mac CPU build.
- Bench against September and maniac, and `POKER_NO_METAL=1` as the A/A comparison.
- Live play is unchanged by construction: this PR touches `tools/` and `results/` only, so no dump runs were done.
- Recording the implementation in `--dump` and refusing to pair across it (#62 covers dump metadata); printing the path at bench start and failing if `metalAvailable()` changes mid-run.
