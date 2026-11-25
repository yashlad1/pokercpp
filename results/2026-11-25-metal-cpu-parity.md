# Metal vs CPU parity (2026-11-25)

Issue #38. Compares a plain CPU build of the engine with a `-DUSE_METAL` build (Apple Silicon, M4). Run with `python tools/metal_parity.py`. On a machine with no Metal build it prints "Metal not available" and exits 0, so CI on Linux skips it.

## Method

- **Builds.** `tools/build_engine.sh` and `tools/build_engine.sh --metal`, each copied to its own directory. The module name is the same, so the script runs each build in its own process.
- **Decision parity.** 1,000 seeded random spots (preflop, flop, turn and river; stacks of 8, 15, 30 and 100 bb; checked-to and facing a bet; 0 to 2 villain raises), 20,000 sims, a fixed engine seed per spot. Both builds return the action plus equity, realized and required.
- **Explaining a disagreement.** The decision gates are equity against 0.30, 0.50, 0.55, 0.62 and 0.75, and realized against required. A disagreement is explained when the nearest of those is within 4 standard errors of a difference of two 20,000-sim estimates (0.020 equity).
- **Control.** The CPU build again on the same spots with different engine seeds. It gives the flip rate of one implementation against itself on this mix.
- **Bench parity.** `tools/bench.py` duplicate-dealt matches, hero `PokerCpp` at 2,000 sims, once per build, same deal seeds, 60,000 hands each, run as 8 processes per build (each process starts with fresh opponent memory; both builds are split the same way). Interval is on the per-pair difference, as in `tools/paired.py`.
- **Pass rule.** More than 99% same action, or no more disagreements than the control plus two standard deviations; every disagreement explained; each bench interval contains 0.

## Decision parity

| Check | Result |
|---|---|
| Same action, Metal vs CPU | 98.6% (986 of 1,000) |
| Disagreements | 14 (1.4%) |
| Control, CPU vs CPU, other seeds | 10 disagreements (1.0%) |
| Disagreements within noise of a threshold | 14 of 14 |

Largest distance from a threshold among the 14: 0.0024 equity, against a band of 0.020. The two equities in each pair differ by 0.0001 to 0.008. Eight sit at the 0.50, 0.55, 0.62 or 0.75 cuts and six at the call gate (realized vs required).

**The 99% bar.** The issue asks for more than 99%. This mix misses it, and so does CPU against itself (99.0% would be 10 flips; the control had 10 and Metal 14, a gap within count noise). The mix is deliberately dense near thresholds, so the share depends on the mix more than on the build. The script therefore treats "no more than the control" as the pass; the strict 99% reading is not met here.

## Bench parity (paired, same seeds)

| Opponent | Hands | CPU hero | Metal hero | Metal minus CPU, bb/100 (95% interval) |
|---|---|---|---|---|
| Reference, 15 bb | 60,000 | +54.1 | +54.0 | -0.2 [-0.6, +0.2] |
| Aggro, 100 bb | 60,000 | +499.0 | +506.4 | +7.3 [-4.3, +19.0] |

Both intervals contain 0.

**Aggro is noisy.** Its per-hand spread is large, so an interval is wide and a fixed-seed run misses 0 about one time in twenty. Earlier runs on other seed sets gave: 6,000 hands +49.9 [+11.5, +88.3] (excluded 0), 12,000 hands -3.2 [-28.0, +21.6], 12,000 hands +11.1 [-15.2, +37.5], 20,000 hands +21.5 [+2.4, +40.7] (excluded 0, overlaps the first set), and a fresh 60,000 hands -3.0 [-14.7, +8.7]. The sign flips across independent sets, which is what chance looks like, but a small Metal edge vs aggro (a few bb/100 on about +500) is not ruled out.

## Detection check (local only, not committed)

A scratch Metal build with 0.03 added to the equity: 93.5% same action (65 disagreements against 10 in the control), exit code 1.

## Not done from the issue

- The linux/amd64 image against the Mac CPU build.
- Bench against September and maniac, and `POKER_NO_METAL=1` as the A/A comparison.
- Recording the implementation in `--dump` and refusing to pair across it (#62 covers dump metadata); printing the path at bench start and failing if `metalAvailable()` changes mid-run.
