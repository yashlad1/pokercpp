# #85 gate results: the call-narrowing candidate (factor 0.6)

Date: 2026-11-26. Issue #85 (child of #53, option built in #84). The rules, seeds and commands are in `results/2026-11-26-85-call-narrow-preregistration.md`; they were committed before any run. The runs are finished and this file only records them. Nothing here ships anything: the candidate never ships, whatever the result, and live stays with the option off (`kCallNarrow = 1.0`).

## Run facts
- **Baseline:** 8f1132498643daf16dd84b58dd2fe903be7ae8c9 (head of PR #139, option off at `kCallNarrow = 1.0`). **Candidate:** 472c9391bf9ee8c16efc29c128ccc919068c5eb1, one local commit on 8f11324, never pushed. Its whole diff, one line in `chipzen/decide.h`:
  - `-constexpr double kCallNarrow = 1.0;`
  - `+constexpr double kCallNarrow = 0.6;`
- **Step 0:** `kCallNarrow` is 1.0 in the baseline and 0.6 in the candidate; `kPreflopRealization = 0.75` and the shove line `stackInBB <= 10.0` are equal in both trees; the candidate diff is that one line (`1 1 chipzen/decide.h`).
- **Step 2 engine hashes (sha256), each module resolved inside its own worktree:**
  - `pokercpp_engine`, baseline worktree: c11df74e3081a731c1bfa2e7046f3f3d998050a7dbc810c102e77d9011f43033
  - `pokercpp_engine`, candidate worktree: 1a067f390399fd34cb08e04fd62e737db7547c9a7a66a1937ed2e1e83b26b9e9
  - `pokercpp_engine_base` (the September module, built once and copied into both worktrees): d83a061259f9e0a1ccf54a680a641398bc4a0574dfdfd43827bef9f2ae93ae97 in both
  - Engine hashes differ, base hashes match, as the record requires.
- **Build path:** `meta.impl` read `cpu` in the first dump of each build.
- **Step 4 (bench, 48 dumps):** 10:57:56 to 11:08:03 UTC (05:57:56 to 06:08:03 Eastern), 607 s, under `xargs -P 10`, so not a timing figure.
- **Step 5 (match, 8 dumps):** 3,177 s, run serially.
- **Step 6 (analysis):** about 2 s. The dry run (step 3) took about 22 s and steps 0 to 2 about 9 s.
- **Seeds:** 780001 and 790001, as registered. Per bench run: 2,000 seat-swapped pairs, `--hero bot --wire live --sims 5000`; match runs 200 pairs each (400 matches), `--hand-cap 1000`.
- **Identity check (step 4):** nit, aggro and maniac were IDENTICAL at both stacks and both seeds. Reference, station and september were `different`. No station row was IDENTICAL, so the identity stop did not fire.
- **Fail-closed checks (step 6):** 48 bench dumps and 8 match dumps present, 24 paired files with one `A - B:` line each, 8 match logs with one `vs ` line each, no "no metadata" warning, and the step 6 `ENGINE FAILED` total was 0.

## Verdict
- **Effect size.** About -37 bb/100 against station at 100 bb (-39.3 and -36.6) is large, not marginal. Against reference the gain is +3.8 on one seed and 0.0 on the other, so there is no benefit evidence.
- **Rule 1 (bench harm): FAIL.**
  - Station 100 bb is `worse` on both seeds:
    - station 100 780001  `A - B: -39.3 bb/100   95% CI [-52.9, -25.7]   worse`
    - station 100 790001  `A - B: -36.6 bb/100   95% CI [-50.5, -22.7]   worse`
  - Station 15 bb is `worse` on 780001 only, and inconclusive on 790001:
    - station 15 780001  `A - B: -21.5 bb/100   95% CI [-31.4, -11.6]   worse`
    - station 15 790001  `A - B: -9.2 bb/100   95% CI [-18.8, +0.4]   inconclusive`
- **Rule 2 (match harm): PASS.** Drops (candidate minus baseline, points): reference 780001 0, reference 790001 +0.2, september 780001 +1.0, september 790001 +1.8. McNemar exact (reported only, not a gate), verbatim from step 6:
  - reference 780001: `vs reference: discordant A-only 0, B-only 0, p=1.0000 (McNemar exact), 400 matches`
  - september 780001: `vs september: discordant A-only 25, B-only 21, p=0.6587 (McNemar exact), 400 matches`
  - reference 790001: `vs reference: discordant A-only 1, B-only 0, p=1.0000 (McNemar exact), 400 matches`
  - september 790001: `vs september: discordant A-only 22, B-only 15, p=0.3240 (McNemar exact), 400 matches`
- **Rule 3 (benefit, gating): MISS for both targets.**
  - Reference 100 bb is `better` on 780001 and inconclusive on 790001:
    - reference 100 780001  `A - B: +3.8 bb/100   95% CI [+0.7, +6.9]   better`
    - reference 100 790001  `A - B: +0.0 bb/100   95% CI [-2.4, +2.5]   inconclusive`
  - Nit 100 bb is IDENTICAL on both seeds (`+0.0 [+0.0, +0.0]`): the rule never fired, because nit rarely calls. The record warns that a nit miss can mean a gain too small to see; here the lists are identical, so there was nothing to see.
- **Rule 4 (control, reported, does not gate):** station is `worse` at 100 bb on both seeds, the pre-stated "expected neutral or worse". The record's expected reading applies: a blanket factor fails on station, so narrowing needs an opponent-aware form (#37).
- **Outcome: the candidate is PARKED with its numbers.** Nothing ships.
  - The option itself (PR #139, off by default) is not merged. Whether to keep it as groundwork for #37 is the owner's call.
  - A second factor value would be a new look and need fresh seeds.
- **Design lesson for future pre-registrations.** Nit was untestable as a target, because the rule never fired against it (IDENTICAL on both seeds). A cheap pre-check of how often the rule fires per opponent, before choosing targets, would have caught that.
- **Live relevance (fact).** In live match 1 the opponent called 16 of 22 of our 2.5 bb opens (73%), which is station-like (`results/2026-11-24-live-log-analysis.md`). A blanket factor would likely have cost there too.
- **Direction for #37.** Make narrowing depend on what the opponent's calls are worth, that is, its observed rate of calling our bets: narrow nothing against a station-like caller and some against a selective one. That needs call stats in the opponent memory, the parked stage-1 stats work on branch `research/opp-stats`. The shared counter `bot._villain_calls` (#139) is reusable.

## All 24 paired lines
Verbatim `A - B` lines from `tools/paired.py`, candidate minus baseline, bb/100, unadjusted 95% intervals. Unadjusted: 2 seed sets, one factor value, one look.

| opponent | stack (bb) | seed 780001 | seed 790001 |
|---|---|---|---|
| reference | 15 | `A - B: -0.1 bb/100   95% CI [-0.3, +0.1]   inconclusive` | `A - B: +0.2 bb/100   95% CI [-0.3, +0.8]   inconclusive` |
| nit | 15 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| station | 15 | `A - B: -21.5 bb/100   95% CI [-31.4, -11.6]   worse` | `A - B: -9.2 bb/100   95% CI [-18.8, +0.4]   inconclusive` |
| aggro | 15 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| maniac | 15 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| september | 15 | `A - B: +3.2 bb/100   95% CI [-1.9, +8.4]   inconclusive` | `A - B: +0.6 bb/100   95% CI [-5.0, +6.1]   inconclusive` |
| reference | 100 | `A - B: +3.8 bb/100   95% CI [+0.7, +6.9]   better` | `A - B: +0.0 bb/100   95% CI [-2.4, +2.5]   inconclusive` |
| nit | 100 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| station | 100 | `A - B: -39.3 bb/100   95% CI [-52.9, -25.7]   worse` | `A - B: -36.6 bb/100   95% CI [-50.5, -22.7]   worse` |
| aggro | 100 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| maniac | 100 | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` | `A - B: +0.0 bb/100   95% CI [+0.0, +0.0]   inconclusive` |
| september | 100 | `A - B: +1.4 bb/100   95% CI [-12.3, +15.2]   inconclusive` | `A - B: +6.1 bb/100   95% CI [-8.7, +20.8]   inconclusive` |
Notes (facts only):
- **IDENTICAL (rule never fired, counted as neutral per the record):** nit, aggro and maniac at 15 and 100 bb, on both seeds (12 rows). **Different:** station, reference and september at both stacks and seeds. No station row was IDENTICAL, so the identity stop did not fire.
- **Reference 15 bb** is near 0: -0.1 on 780001 and +0.2 on 790001, both inconclusive. These are reported only.
- **September rows** are all inconclusive. September is unseeded, so its rows are paired on the hero side only and never IDENTICAL.
- **Nit 15 bb** is IDENTICAL on both seeds (`+0.0`), as at 100 bb.

## The 8 match lines
- `match-base-reference-780001.txt: vs reference    400/400 = 100.0% [99.0%, 100.0%]   pairs lost both 0 / split 0 / won both 200   avg 89.9 hands/match`
- `match-base-september-780001.txt: vs september    190/400 = 47.5% [42.7%, 52.4%]   pairs lost both 29 / split 152 / won both 19   avg 50.4 hands/match`
- `match-cand-reference-780001.txt: vs reference    400/400 = 100.0% [99.0%, 100.0%]   pairs lost both 0 / split 0 / won both 200   avg 89.5 hands/match`
- `match-cand-september-780001.txt: vs september    194/400 = 48.5% [43.6%, 53.4%]   pairs lost both 28 / split 150 / won both 22   avg 50.1 hands/match`
- `match-base-reference-790001.txt: vs reference    399/400 = 99.8% [98.6%, 100.0%]   pairs lost both 0 / split 1 / won both 199   avg 89.0 hands/match`
- `match-base-september-790001.txt: vs september    180/400 = 45.0% [40.2%, 49.9%]   pairs lost both 34 / split 152 / won both 14   avg 45.4 hands/match`
- `match-cand-reference-790001.txt: vs reference    400/400 = 100.0% [99.0%, 100.0%]   pairs lost both 0 / split 0 / won both 200   avg 89.2 hands/match`
- `match-cand-september-790001.txt: vs september    187/400 = 46.8% [41.9%, 51.6%]   pairs lost both 30 / split 153 / won both 17   avg 46.1 hands/match`
## Dry run and fidelity
**(a) Dry run.** Before the real run, steps 4 to 6 ran with the dry-run values (`--hands 40`, `--sims 200`, `--matches 2`, seeds 1 and 2) in a scratch folder. `DRY RUN STEPS OK` printed and the `ENGINE FAILED` count printed 0. The dry numbers are meaningless and are not reported; the scratch folder was deleted. Step 6 on the real run also reported an `ENGINE FAILED` total of 0.

**(b) Fidelity.** All seven step scripts (0 to 6) are byte-identical to the record's command blocks: the `diff` of each script against its block printed "identical" for every step. The variables come from a separate environment wrapper (`PY`, `BASE_WT`, `CAND_WT`, `OUT`, `OPPS`, `HANDS`, `SIMS`, `MATCHES`, `S1`, `S2`), exported before each step, and are not written into the scripts.
