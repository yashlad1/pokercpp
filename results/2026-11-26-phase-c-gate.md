# Phase C gate results: the 0.85 candidate

Date: 2026-11-26. Phase C, steps C3 (bench and match gate) and C4 (image gate). The rules, seeds and commands are in `results/2026-11-26-c1-preregistration.md`; they were committed before any run. The runs are finished and this file only records them. Nothing here ships anything: live stays at `kPreflopRealization` 0.75 until the owner decides (stop S-C).

## Run facts
- **Baseline:** 38956e4819f9d0d351728e8f0096ab9a8ad4753f (main, 0.75). **Candidate:** 0eff667ad5bbee7c893e92ff165fce8639166030 (0.85). Step 0 printed `kPreflopRealization = 0.75` and `= 0.85`; the bot, opponent, bench, match and paired files differ by 0 bytes between the two trees.
- **Step 2 engine hashes (sha256), each module resolved inside its own worktree:**
  - `pokercpp_engine`, baseline worktree: a8286822bad4675e03251bd670548009e58f32fe8ef03107a08efe71d71a2756
  - `pokercpp_engine`, candidate worktree: bc93045f851ec8d5e96293a092ca7cb130668a017882bb07fd9a86682dfa2088
  - `pokercpp_engine_base` (the September module, built once and copied into both worktrees): 0cc359dfdc757c54c69bd062508889d4f50febe91b112a05e295e273ce194c91 in both
  - Engine hashes differ, base hashes match, as the record requires.
- **Build path:** `meta.impl` read `cpu` in the first dump of each build.
- **Step 3 (bench, 180 dumps):** 2026-11-26 07:44:09 to 08:07:22 UTC (02:44:09 to 03:07:22 Eastern), 23 min 13 s. It ran under `xargs -P 10` alongside another job, so this wall time is not a timing figure.
- **Step 4 (match, 8 dumps):** 08:07:28 to 08:58:25 UTC (03:07:28 to 03:58:25 Eastern), 50 min 57 s, run serially.
- **Seeds:** 740001 and 750001, as registered. Per run: 2,000 seat-swapped pairs, `--hero bot --wire live --sims 5000`; match runs 200 pairs each (400 matches), `--hand-cap 1000`.

## Verdict
- **Rule 1 (bench harm): PASS.** No row is `worse` on both seed sets. Rows `worse` on one set only are on seed 750001: station and loosepassive at 15, 25 and 100 bb. Every row on 740001 is `better` or `inconclusive`. The six lines:
- station 15 750001  `A - B: -1.3 bb/100   95% CI [-2.6, -0.0]   worse`
- loosepassive 15 750001  `A - B: -1.3 bb/100   95% CI [-2.6, -0.0]   worse`
- station 25 750001  `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse`
- loosepassive 25 750001  `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse`
- station 100 750001  `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse`
- loosepassive 100 750001  `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse`
- **Rule 2 (match harm): PASS.** Drops (candidate minus baseline, points): reference 740001 0, reference 750001 -0.2, september 740001 0.0, september 750001 -1.5. None is worse than -5 on both sets. McNemar exact p values (reported only, not a gate):
  - reference 740001: discordant A-only 0, B-only 0, p=1.0000
  - september 740001: discordant A-only 17, B-only 17, p=1.0000
  - reference 750001: discordant A-only 0, B-only 1, p=1.0000
  - september 750001: discordant A-only 14, B-only 20, p=0.3915
- **Rule 3 (benefit, reported, not a gate): DOES NOT REPLICATE.** Aggro 15 bb is `better` on 740001 (+40.0, [+23.3, +56.8]) but `inconclusive` on 750001 (+9.2, [-7.2, +25.5]). The reference 15 bb part holds: the point estimates are -0.2 and +0.4, not below 0 on both.
- **Rule 4 (outcome):** the harm gates pass, so the candidate is not parked on harm. Rule 3 did not replicate, so per the record the reviewers recommend parking and the owner decides (stop S-C). Live stays 0.75 until the owner says otherwise.

## All 90 paired lines
Verbatim `A - B` lines from `tools/paired.py`, candidate minus baseline, bb/100, unadjusted 95% intervals.

| opponent | stack (bb) | seed 740001 | seed 750001 |
|---|---|---|---|
| reference | 15 | `A - B: -0.2 bb/100   95% CI [-1.6, +1.2]   inconclusive` | `A - B: +0.4 bb/100   95% CI [-1.4, +2.2]   inconclusive` |
| reference | 25 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +2.1 bb/100   95% CI [+0.1, +4.1]   better` |
| reference | 100 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +1.9 bb/100   95% CI [-0.4, +4.1]   inconclusive` |
| station | 15 | `A - B: -0.4 bb/100   95% CI [-2.1, +1.2]   inconclusive` | `A - B: -1.3 bb/100   95% CI [-2.6, -0.0]   worse` |
| station | 25 | `A - B: -0.5 bb/100   95% CI [-2.0, +1.0]   inconclusive` | `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse` |
| station | 100 | `A - B: -0.5 bb/100   95% CI [-2.0, +1.0]   inconclusive` | `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse` |
| nit | 15 | `A - B: -0.1 bb/100   95% CI [-2.6, +2.3]   inconclusive` | `A - B: +0.5 bb/100   95% CI [-1.8, +2.9]   inconclusive` |
| nit | 25 | `A - B: +2.1 bb/100   95% CI [-1.3, +5.5]   inconclusive` | `A - B: +1.6 bb/100   95% CI [-1.7, +4.8]   inconclusive` |
| nit | 100 | `A - B: +0.5 bb/100   95% CI [-7.6, +8.5]   inconclusive` | `A - B: -2.1 bb/100   95% CI [-6.3, +2.1]   inconclusive` |
| maniac | 15 | `A - B: -0.3 bb/100   95% CI [-7.5, +6.9]   inconclusive` | `A - B: -3.3 bb/100   95% CI [-9.6, +3.0]   inconclusive` |
| maniac | 25 | `A - B: -2.5 bb/100   95% CI [-15.0, +9.9]   inconclusive` | `A - B: +6.4 bb/100   95% CI [-6.5, +19.3]   inconclusive` |
| maniac | 100 | `A - B: +0.3 bb/100   95% CI [-46.1, +46.8]   inconclusive` | `A - B: -15.1 bb/100   95% CI [-62.1, +32.0]   inconclusive` |
| aggro | 15 | `A - B: +40.0 bb/100   95% CI [+23.3, +56.8]   better` | `A - B: +9.2 bb/100   95% CI [-7.2, +25.5]   inconclusive` |
| aggro | 25 | `A - B: +73.5 bb/100   95% CI [+45.3, +101.7]   better` | `A - B: +23.9 bb/100   95% CI [-1.8, +49.7]   inconclusive` |
| aggro | 100 | `A - B: +378.5 bb/100   95% CI [+287.5, +469.4]   better` | `A - B: +154.9 bb/100   95% CI [+67.0, +242.8]   better` |
| switcher | 15 | `A - B: -7.5 bb/100   95% CI [-25.7, +10.6]   inconclusive` | `A - B: +1.0 bb/100   95% CI [-16.4, +18.4]   inconclusive` |
| switcher | 25 | `A - B: -13.8 bb/100   95% CI [-43.8, +16.3]   inconclusive` | `A - B: +7.3 bb/100   95% CI [-20.8, +35.4]   inconclusive` |
| switcher | 100 | `A - B: -72.9 bb/100   95% CI [-188.2, +42.4]   inconclusive` | `A - B: +48.8 bb/100   95% CI [-60.5, +158.1]   inconclusive` |
| loosepassive | 15 | `A - B: -0.4 bb/100   95% CI [-2.1, +1.2]   inconclusive` | `A - B: -1.3 bb/100   95% CI [-2.6, -0.0]   worse` |
| loosepassive | 25 | `A - B: -0.5 bb/100   95% CI [-2.0, +1.0]   inconclusive` | `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse` |
| loosepassive | 100 | `A - B: -0.5 bb/100   95% CI [-2.0, +1.0]   inconclusive` | `A - B: -1.4 bb/100   95% CI [-2.6, -0.1]   worse` |
| random | 15 | `A - B: +24.7 bb/100   95% CI [+14.9, +34.5]   better` | `A - B: +13.3 bb/100   95% CI [+4.2, +22.4]   better` |
| random | 25 | `A - B: +27.3 bb/100   95% CI [+11.4, +43.2]   better` | `A - B: +28.5 bb/100   95% CI [+13.9, +43.1]   better` |
| random | 100 | `A - B: +98.5 bb/100   95% CI [+47.3, +149.7]   better` | `A - B: +61.5 bb/100   95% CI [+15.4, +107.5]   better` |
| bluff0 | 15 | `A - B: -0.2 bb/100   95% CI [-1.6, +1.2]   inconclusive` | `A - B: +0.4 bb/100   95% CI [-1.4, +2.2]   inconclusive` |
| bluff0 | 25 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +2.1 bb/100   95% CI [+0.1, +4.1]   better` |
| bluff0 | 100 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +1.9 bb/100   95% CI [-0.4, +4.1]   inconclusive` |
| bluff25 | 15 | `A - B: -0.3 bb/100   95% CI [-1.7, +1.2]   inconclusive` | `A - B: +0.2 bb/100   95% CI [-1.6, +1.9]   inconclusive` |
| bluff25 | 25 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +1.8 bb/100   95% CI [-0.2, +3.8]   inconclusive` |
| bluff25 | 100 | `A - B: +1.2 bb/100   95% CI [-0.3, +2.6]   inconclusive` | `A - B: +1.6 bb/100   95% CI [-0.6, +3.8]   inconclusive` |
| bluff50 | 15 | `A - B: -0.7 bb/100   95% CI [-2.2, +0.8]   inconclusive` | `A - B: +0.3 bb/100   95% CI [-1.6, +2.2]   inconclusive` |
| bluff50 | 25 | `A - B: +0.5 bb/100   95% CI [-1.3, +2.3]   inconclusive` | `A - B: +1.9 bb/100   95% CI [-0.2, +4.0]   inconclusive` |
| bluff50 | 100 | `A - B: +0.8 bb/100   95% CI [-0.7, +2.3]   inconclusive` | `A - B: +1.7 bb/100   95% CI [-0.6, +4.1]   inconclusive` |
| loosebluff0 | 15 | `A - B: +8.1 bb/100   95% CI [+5.1, +11.2]   better` | `A - B: +3.5 bb/100   95% CI [+0.7, +6.3]   better` |
| loosebluff0 | 25 | `A - B: +8.9 bb/100   95% CI [+5.5, +12.4]   better` | `A - B: +3.5 bb/100   95% CI [+0.6, +6.5]   better` |
| loosebluff0 | 100 | `A - B: +9.4 bb/100   95% CI [+5.3, +13.5]   better` | `A - B: +2.9 bb/100   95% CI [-0.6, +6.5]   inconclusive` |
| loosebluff25 | 15 | `A - B: +8.8 bb/100   95% CI [+5.1, +12.4]   better` | `A - B: +3.5 bb/100   95% CI [+0.2, +6.8]   better` |
| loosebluff25 | 25 | `A - B: +10.2 bb/100   95% CI [+6.1, +14.4]   better` | `A - B: +4.2 bb/100   95% CI [+0.7, +7.7]   better` |
| loosebluff25 | 100 | `A - B: +8.1 bb/100   95% CI [+2.6, +13.6]   better` | `A - B: +3.3 bb/100   95% CI [-0.9, +7.4]   inconclusive` |
| loosebluff50 | 15 | `A - B: +7.8 bb/100   95% CI [+4.0, +11.5]   better` | `A - B: +7.6 bb/100   95% CI [+3.8, +11.3]   better` |
| loosebluff50 | 25 | `A - B: +8.5 bb/100   95% CI [+4.1, +13.0]   better` | `A - B: +7.2 bb/100   95% CI [+3.1, +11.3]   better` |
| loosebluff50 | 100 | `A - B: +6.6 bb/100   95% CI [-0.1, +13.3]   inconclusive` | `A - B: +5.4 bb/100   95% CI [-0.1, +10.9]   inconclusive` |
| september | 15 | `A - B: -1.4 bb/100   95% CI [-6.9, +4.0]   inconclusive` | `A - B: -3.7 bb/100   95% CI [-8.5, +1.2]   inconclusive` |
| september | 25 | `A - B: -3.3 bb/100   95% CI [-10.0, +3.4]   inconclusive` | `A - B: -2.7 bb/100   95% CI [-9.1, +3.7]   inconclusive` |
| september | 100 | `A - B: +10.6 bb/100   95% CI [-6.4, +27.7]   inconclusive` | `A - B: -3.0 bb/100   95% CI [-19.6, +13.6]   inconclusive` |

Notes (facts only):
- 90 rows with unadjusted 95% intervals were read. Rows other than the rule 3 targets are not evidence for adoption on their own.
- **Identical lines.** bluff0's lines equal reference's, and loosepassive's equal station's, at every stack and both seeds (12 of 12 line pairs each). bluff25 and bluff50 do not match reference everywhere (bluff25 equals it only at 25 and 100 bb on 740001; bluff50 nowhere). So the number of distinct opponents is smaller than 15.
- **Rows `better` on both sets:** random at 15, 25 and 100 bb; aggro at 100 bb; loosebluff0, loosebluff25 and loosebluff50 at 15 and 25 bb. Rows `better` on one set only: aggro 15 and 25 bb, loosebluff0 and loosebluff25 at 100 bb (740001 only); reference 25 bb and bluff0 25 bb (750001 only).

## The 8 match lines
- `match-base-reference-740001.txt: vs reference    396/400 = 99.0% [97.5%, 99.6%]   pairs lost both 0 / split 4 / won both 196   avg 89.7 hands/match`
- `match-base-reference-750001.txt: vs reference    399/400 = 99.8% [98.6%, 100.0%]   pairs lost both 0 / split 1 / won both 199   avg 90.7 hands/match`
- `match-base-september-740001.txt: vs september    190/400 = 47.5% [42.7%, 52.4%]   pairs lost both 27 / split 156 / won both 17   avg 44.3 hands/match`
- `match-base-september-750001.txt: vs september    195/400 = 48.8% [43.9%, 53.6%]   pairs lost both 27 / split 151 / won both 22   avg 49.6 hands/match`
- `match-cand-reference-740001.txt: vs reference    396/400 = 99.0% [97.5%, 99.6%]   pairs lost both 0 / split 4 / won both 196   avg 89.0 hands/match`
- `match-cand-reference-750001.txt: vs reference    398/400 = 99.5% [98.2%, 99.9%]   pairs lost both 0 / split 2 / won both 198   avg 89.8 hands/match`
- `match-cand-september-740001.txt: vs september    190/400 = 47.5% [42.7%, 52.4%]   pairs lost both 28 / split 154 / won both 18   avg 43.5 hands/match`
- `match-cand-september-750001.txt: vs september    189/400 = 47.2% [42.4%, 52.1%]   pairs lost both 29 / split 153 / won both 18   avg 47.5 hands/match`

## C4: image gate
- Image built for linux/amd64 from 0eff667. `chipzen-sdk validate --check-connectivity` printed "All checks passed (1 warning)" (the warning is an `os` import).
- In the image, `test_bot_sdk`, `test_v4` and `test_preflop_realization` pass. `bot.py` and `opponent.py` sha256 equal the tree. The in-image PREFLOP spot realized/equity reads 0.85.
- A `--no-cache` rebuild gives a bit-identical `.so`. The tarball is 21.9 MB and was not uploaded.
- `POKERCPP_COMMIT` reads "unknown" in the image because no `GIT_SHA` build argument was passed. Any upload build must pass it.

## Deviations
1. Step 0's diff also touched `chipzen/README.md`, `tools/mutants/SOURCES.md` and `tools/mutants/catalogue.json` (no play effect; accepted by the reviewer before the runs).
2. Step 2's `modpath` check, run from inside `$OUT`, first printed the September module path under `$OUT`, because Python puts the current directory on `sys.path`. Rerun from `/`, each path resolved inside its own worktree with the same hash. The record's command should be run from a neutral directory; later pre-registrations that copy it (#126's) must do the same.
3. The runner was interrupted by a usage limit after step 4 and resumed for step 5. Nothing was rerun, and no result file was read before step 5's checks passed.

## Log
Rows R432 to R521 (Runs, 90 paired rows) and M035 to M042 (Matches, 8 rows) in `results/eval-log.xlsx`, experiment `phase-c-gate-0.85`, plus two Timing rows for steps 3 and 4. `tools/evlog.py` rounds the interval before choosing a verdict, so it showed station and loosepassive at 15 bb on 750001 (upper bound -0.0) as inconclusive; those two rows (R478, R483) were set to `worse`, matching `paired.py`.

