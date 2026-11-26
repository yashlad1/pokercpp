# Exploratory round E1-E4: where the Chipzen bot loses, and which cheap change helps

Records only. Nothing here ships and nothing was merged. Eval-log rows R348-R391 (44 paired comparisons; the E1 split is one run, recorded below, not a paired comparison).

## Goal, rules, pre-stated call
- **Goal.** Find where the bot loses at 15 bb (the Chipzen depth) and test three cheap changes: shove threshold (E3), call margin on large turn/river bets (E4), and 20000 vs 5000 sims (E2). E1 splits the base result by seat and by how the hand ended.
- **Rules.** Seeds 810001 and 820001 only; `--hero bot --wire live --sims 5000`, 2,000 duplicate pairs (4,000 hands) per cell. Base = main at 8fb39f1. Paired maths is `tools/paired.py` at that commit.
- **Pre-stated "promising" rule.** The target opponent is above 0 on both seeds and no control opponent is below 0 on both.
- **Call: no variant passed.** shove-15 is above 0 on the controls but its target (aggro 15) is +8.9 / -2.2, both crossing 0. About 70 rows were looked at, intervals not adjusted.

## E1: base vs aggro at 15 bb, split (inst run, 5000 sims)
| cut | s1 bb/100 [95% CI] | s2 bb/100 [95% CI] |
|---|---|---|
| total | -0.1 [-21.7,+21.6] | +5.4 [-16.6,+27.3] |
| hero big blind (50% of hands) | -11.0 [-27.1,+5.1] | -7.8 [-23.6,+8.0] |
| hero small blind (50%) | +10.9 [-9.0,+30.9] | +13.2 [-7.1,+33.5] |
| hero folds preflop (66.7%) | -74.8 [-76.7,-72.8] | -74.8 [-76.8,-72.9] |
| postflop (31%) | +61.2 [+40.1,+82.3] | +64.0 [+42.8,+85.3] |
| preflop all-in (2%) | +13.5 [+7.0,+20.0] | +16.1 [+9.1,+23.1] |

There is no loss to find at 15 bb vs aggro. The seat split is noise (all intervals cross 0). The cost sits in preflop folds; postflop play pays it back.

## E2: 20000 vs 5000 sims (candidate = base build, 20000 sims; B = base at 5000)
| opp, stack | diff s1 | diff s2 |
|---|---|---|
| aggro 15 | +0.4 [-5.4,+6.2] | +0.8 [-5.6,+7.2] |
| aggro 100 | +6.3 [-23.4,+35.9] | **-37.2 [-70.5,-3.8]** |
| reference 15 | +0.1 [-0.4,+0.5] | -0.8 [-2.3,+0.6] |
| reference 100 | +0.3 [-0.3,+0.8] | -0.8 [-2.9,+1.4] |
| september 15 | +0.3 [-5.3,+5.9] | -3.0 [-8.3,+2.4] |
| september 100 | +7.8 [-6.0,+21.5] | -12.5 [-28.0,+3.0] |

No evidence of a gain. The one interval off 0 (aggro 100, s2) is negative and not repeated on s1. Latency at 20000 sims: p50 13-14 ms, p99 24-26 ms, max 71-98 ms (n about 23k-27k decisions per cell group). The machine ran 10-14 jobs at once, so these latencies are inflated by load.

## E3: shove threshold (diff vs base, bb/100)
`exp/shove-12`: identical to base on every cell. The check uses the stack after the blind, so it never fires from a 15 bb start (aggro 15 diff is exactly 0.0 on both seeds).

`exp/shove-15` (`stackInBB <= 15.0`):
| opp, stack | diff s1 | diff s2 | both seeds |
|---|---|---|---|
| aggro 15 (target) | +8.9 [-3.0,+20.8] | -2.2 [-14.6,+10.2] | inconclusive |
| reference 15 | +5.0 [+2.1,+7.8] | +5.2 [+2.7,+7.7] | better |
| nit 15 | +6.6 [+4.0,+9.1] | +6.1 [+3.7,+8.6] | better |
| station 15 | +34.8 [+17.0,+52.6] | +51.1 [+33.3,+69.0] | better |
| reference 25 | +0.6 [-0.6,+1.8] | +0.3 [-1.0,+1.6] | neutral |

## E4: call margin 0.03 on turn/river bets over half the pot (diff vs base)
| opp, stack | diff s1 | diff s2 |
|---|---|---|
| aggro 15 (target) | 0.0 [0.0,0.0] | 0.0 [0.0,0.0] |
| aggro 100 (target) | -17.9 [-46.7,+10.8] | **-42.8 [-72.3,-13.2]** |
| september 15 (target) | +4.0 [-0.7,+8.6] | +0.7 [-4.3,+5.6] |
| september 100 (target) | +8.4 [-3.7,+20.4] | -6.8 [-23.1,+9.4] |
| reference 15 | +0.1 [-0.1,+0.2] | -0.4 [-1.2,+0.4] |
| reference 100 | +0.2 [-0.0,+0.4] | -0.4 [-1.2,+0.5] |

Never fires at 15 bb. At aggro 100 it hurts on s2. Everything else is no evidence.

## Commands
```
python tools/bench.py --hero bot --wire live --sims 5000 --vs <opp> --stack <bb> --hands 4000 --seed0 <810001|820001> --dump <out>.json
python tools/paired.py <candidate>.json <base>.json
python tools/evlog.py paired results/eval-log.xlsx <candidate>.json <base>.json --experiment ... (one call per row)
```
E1 and E2 used a local instrumented wrapper of the bench loop (per-hand end type, seat, decision latency); it is not committed. The 20000-sim dumps carry a different sims label, so paired.py needed it equalised for those comparisons only; the eval-log rows do not need it.

## Branches (local only, never pushed)
- `exp/shove-12` 8f01da8, `exp/shove-15` 42d28ff, `exp/call-margin-0.03` b9bbd20, each one commit on base 8fb39f1.
```diff
# shove-12 (chipzen/decide.h)
-    if (stackInBB <= 10.0 && equity >= 0.55) {
+    if (stackInBB <= 12.0 && equity >= 0.55) {
# shove-15
-    if (stackInBB <= 10.0 && equity >= 0.55) {
+    if (stackInBB <= 15.0 && equity >= 0.55) {
# call-margin-0.03, after `if (shaded <= d.required) { d.action = "fold"; return d; }`
+    if (board.size() >= 4 && 2 * toCall > pot - toCall && shaded < d.required + 0.03) { d.action = "fold"; return d; }
```

## Limits
- **Exploratory.** Two seeds, about 70 looks, unadjusted intervals; one "worse" cell of that many is expected by chance.
- **september** is a fixed-seed stand-in for the September opponent, not the real one.
- **Latency** runs shared the machine with 10-14 other jobs.
- Paired runs on the same deals, so shared-seed results are not independent of each other.

## Leads
- **shove-15 on non-aggro opponents** is a new hypothesis: it needs its own pre-registered gate on fresh seeds, plus match mode, before anything ships. Tracked in a new issue (see #52).
- **E1** supports the Phase C preflop candidate: the cost at 15 bb is in preflop folds (-74.8 bb/100), not in postflop play.
- **E2 and E4** park on this evidence (#54).
