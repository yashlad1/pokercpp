# C1 pre-registration: the 0.85 preflop candidate

Date: 2026-11-26. Phase C, step C1 (checklist section 6). This record is committed before any gate run. It states the rule, the seeds, the runs and the exact commands. Nothing below was run for a result; only the timing in the last section was measured.

## Candidate
- **Change:** `kPreflopRealization` 0.75 to 0.85 in `chipzen/decide.h`. Nothing else in the C2 diff except the pins that held 0.75 (test_solver "discount must still apply", test_preflop_realization's default, any constant in test_decide_constants), updated by the tester.
- **Baseline:** the main commit the C2 branch forks from, in its own worktree: **38956e4** (main with #121 and #127 merged). C2 forks from current main. Merging this record adds only a results file and timing rows, so a fork taken after it is code-identical; the gate-results file names the exact SHA used. Both builds use the same `chipzen/bot.py`, `tools/bench.py` and `tools/match.py`.
- **Deslop branch:** `refactor/deslop-ai-code` (byte-identical on 83 behavior pins) may merge before the ship decision. If the owner ships 0.85 after that, the one-line change is rebased onto the new main, and the 83 pins plus the image gate are re-run on the rebased candidate before merge.
- **Engine build:** both engines are built with `tools/build_engine.sh`'s default, no `--metal`. That is the CPU path the shipped image runs. Step 2 checks that `meta.impl` reads `cpu` in the first dump of each build.
- **Order:** #121 (`match.py --wire`) is on main; the match commands need it.
- **Live bot today:** 0.75. A pass does not ship anything; the owner decides (checklist section 8).

## Seeds and looks
- **Gate seeds:** 740001 and 750001. Bench pair k uses seed0 + k, so 740001 to 742000 and 750001 to 752000. Match pair m uses seed0 + m, so 740001 to 740200 and 750001 to 750200.
- **Fresh:** neither set was used for any run on main or in the notes.
- **Not fresh, so not used:** 700001 and 710001 (the #81 and #82 looks, and the 12-opponent check; #81 is `results/2026-11-25-preflop-realization-15bb.md`, #82 is `results/2026-11-25-preflop-realization-25-100bb.md`, on main since #127 merged; they informed the choice of 0.85). 720001 and 730001 gated the bluff detector on 24 Nov.
- **Looks counted:** two variants were tried before this gate, 0.85 and 0.95 (#81, #82). Only 0.85 is gated here. The intervals below are unadjusted 95% intervals; the count is reported, not corrected for.

## Runs
- **Bench, per build and seed set:** all 15 opponents by name, one run each, at 15, 25 and 100 bb: reference, station, nit, maniac, aggro, switcher, loosepassive, random, bluff0, bluff25, bluff50, loosebluff0, loosebluff25, loosebluff50, september. That is 45 runs. Each is 2,000 seat-swapped pairs (`--hands 4000`), `--hero bot --wire live --sims 5000`.
- **Match, per build and seed set:** reference and september, 200 pairs each (400 matches: every pair is played twice with the seats swapped), `--hand-cap 1000`, `--hero bot --wire live --sims 5000`.
- **Blind schedule:** "live Chipzen steps every 20 hands" (`blinds_for` in `tools/match.py`, default). 100 bb stack, first big blind 100, the big blind steps 100, 150, 200, 300, 400, 600, 800 every 20 hands, no antes. Levels past hand 140 are extrapolated, never seen live. At the hand cap the agent seated first wins on level chips.
- **Totals:** 180 bench dumps and 8 match dumps.

## Decision rules (fixed now)
Every comparison is candidate minus baseline on the same deals. The commands below always pass the candidate dump first, so `tools/paired.py`'s `A - B` line is candidate minus baseline and "below 0" means the candidate is worse.

1. **Chip-count gate (harm).** A row is one (opponent, stack) pair. A row fails when its paired `A - B` 95% interval lies entirely below 0 (`paired.py` verdict "worse") on both seed sets. The candidate may go forward only if no row fails. The record will list every row that fails, and every row that is below 0 on one set only.
2. **Match gate (harm).** Win rate is wins over 400 matches, from the `vs X k/n` line. Drop is candidate win rate minus baseline win rate, in points. The gate fails if the drop is worse than -5 points on both seed sets, against reference or against september. `match.py --compare` (McNemar) is also reported but does not gate.
3. **Benefit check (reported, not a gate).** At 15 bb against aggro, the paired gain's 95% interval is entirely above 0 on both seed sets, and the paired point estimate against reference at 15 bb is not below 0 on both. If it does not replicate, the reviewers recommend parking and the owner decides.
4. **Outcome.** A failed gate parks the candidate with its numbers, and live stays at 0.75 (stop S-C). A pass hands the candidate to C3 and C4. Shipping is the owner's call.
5. **No peeking; crashes.** No result number is read until all 188 dumps exist. Step 3's `bench.py` output and step 4's `match.py` output go to log files under `$OUT`, with no `tee`; the person running sees only `IDENTICAL` or `different` and exit codes until then. A crash means the whole set is rerun from step 2. A `paired.py` "no metadata" warning counts as a failed pairing and also means a rerun. Step 5 fails closed: no verdict is read unless all 90 paired files hold exactly one `A - B:` line and all 8 match logs exactly one `vs ` line.

## What the rules can and cannot see
- **Half-widths (95%, paired, 0.85 minus 0.75, 2,000 pairs, engine hero, 2,000 sims, from #81 and #82; see the September limits below).** At 15 bb: about ±16 to ±17 against aggro, about ±2 against reference. At 25 bb: about ±27 to ±28 against aggro, ±2 to ±2.5 against reference. At 100 bb: about ±87 to ±92 against aggro, ±2 to ±4 against reference. The 100 bb aggro rows can only fail on a very large loss.
- **Chip gate false-fail rate (no real effect anywhere, normal approximation):** about 2.5% per row per set, so about 0.06% per row on both sets and about 3% over 45 rows.
- **Match gate false-fail rate for a build with no real change:** about 1% per opponent. At 400 matches and a 50% win rate, a win-rate difference has a standard deviation of about 3.5 points, so a drop over 5 points happens about 8% per set and about 0.6% on both. This assumes independent sets.
- **September limits.** (a) The September module cannot be seeded, so september rows are paired on the hero side only. Their intervals will be wider than the #81 half-widths quoted. (b) The identity check cannot fire on september rows, because the two runs differ whatever the candidate does; the other 14 opponents, aggro first, carry it. (c) The match gate's 3.5-point standard deviation is already the unpaired figure, so its false-fail estimate still holds against september.

## Commands
Each step is a script run with `bash`, so `exit` stops the run. Set these once. The same `$PY` (pybind11, pokerkit and openpyxl installed) is used for every command.

```
PY=<python with pybind11 and pokerkit>
BASE_WT=<worktree of the baseline commit>
CAND_WT=<worktree of the C2 branch>
OUT=<new empty directory for dumps and logs>
OPPS="reference station nit maniac aggro switcher loosepassive random bluff0 bluff25 bluff50 loosebluff0 loosebluff25 loosebluff50 september"
```

**Step 0, preconditions.**
```
for WT in $BASE_WT $CAND_WT; do grep -c -- '--wire' $WT/tools/match.py; done    # both must be 1 or more (#121 merged)
git -C $BASE_WT rev-parse HEAD                                                  # record: the baseline SHA
git -C $CAND_WT diff --stat $(git -C $BASE_WT rev-parse HEAD)..HEAD              # decide.h and the pinned tests only
grep -n 'kPreflopRealization =' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h   # 0.75 and 0.85
```

**Step 1, the September module, built once and copied.** Two separate builds hash differently (observed on 26 Nov), so the same file goes into both worktrees.
```
T=$(mktemp -d)
git -C $BASE_WT archive c057f40 chipzen montecarlo model | tar -x -C $T
sed -i.bak 's/PYBIND11_MODULE(pokercpp_engine,/PYBIND11_MODULE(pokercpp_engine_base,/' $T/chipzen/pokercpp_engine.cpp
EXT=$($PY -c 'import sysconfig;print(sysconfig.get_config_var("EXT_SUFFIX"))')
( cd $T && clang++ -std=c++17 -O2 -shared -fPIC -undefined dynamic_lookup $($PY -m pybind11 --includes) \
  chipzen/pokercpp_engine.cpp montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp \
  -o $OUT/pokercpp_engine_base$EXT )
cp $OUT/pokercpp_engine_base$EXT $BASE_WT/chipzen/ && cp $OUT/pokercpp_engine_base$EXT $CAND_WT/chipzen/
```

**Step 2, rebuild each engine right before the runs, then check provenance.** The default build, no `--metal`.
```
modpath() { PYTHONPATH=$1/chipzen $PY -c "import $2;print($2.__file__)"; }     # the file Python imports, as bench.py does
for WT in $BASE_WT $CAND_WT; do (cd $WT && PY=$PY tools/build_engine.sh) || exit 1; done
for M in pokercpp_engine pokercpp_engine_base; do for WT in $BASE_WT $CAND_WT; do
  echo "$M $WT $(modpath $WT $M)"; shasum -a 256 "$(modpath $WT $M)" || exit 1
done; done                                    # record all four; engine hashes must differ, base hashes must match
for L in base cand; do                        # september must import; the dump shows the build is CPU
  WT=$BASE_WT; [ $L = cand ] && WT=$CAND_WT
  (cd $WT && $PY tools/bench.py --hero bot --wire live --sims 100 --vs september --hands 2 --seed0 1 --dump $OUT/check-$L.json) > $OUT/check-$L.log 2>&1 || exit 1
  $PY -c "import json,sys; sys.exit(json.load(open(sys.argv[1]))['meta']['impl'] != 'cpu')" $OUT/check-$L.json || { echo "$L is not cpu"; exit 1; }
done
```
Stop if the two engine hashes are equal, the two base hashes differ, a printed module path is outside its own worktree, the september check fails, or `meta.impl` is not `cpu`.

**Step 3, bench runs, with the identity check inside each row.** A row runs the baseline, then the candidate, then compares the two `results` lists and prints only `IDENTICAL` or `different`, never a number. The `bench.py` output goes to `$OUT/bench-*.log`. Any failing command, or an `IDENTICAL` row, stops everything and goes to the lead. The first row (aggro, 15 bb, seed 740001) runs alone, so a bad setup stops early. The other 89 rows run under `xargs -P` with at most 10 jobs. Every pair is seeded from seed0 + k, so job order does not change the dumps (the september rows are unseeded either way, see the limits). Wall time of the parallel grid is not a timing figure: its start and end are saved in `$OUT/step3-start.txt` and `step3-end.txt`, and the load is logged separately as its own Timing row.
```
cat > $OUT/row.sh <<'EOF'
#!/bin/bash
set -e; trap 'exit 255' ERR          # any failure, or an IDENTICAL row, makes xargs stop launching new rows
o=$1; st=$2; SEED=$3
for pair in "base:$BASE_WT" "cand:$CAND_WT"; do
  L=${pair%%:*}; WT=${pair#*:}
  (cd $WT && $PY tools/bench.py --hero bot --wire live --sims 5000 --vs $o --stack $st --hands 4000 --seed0 $SEED \
     --dump $OUT/$L-$o-$st-$SEED.json) > $OUT/bench-$L-$o-$st-$SEED.log 2>&1
done
r=$($PY -c "import json,sys; a,b=(json.load(open(p))['results'] for p in sys.argv[1:]); print('IDENTICAL' if a==b else 'different')" $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json)
echo "$o $st $SEED $r"; [ "$r" = different ]
EOF
chmod +x $OUT/row.sh; export PY BASE_WT CAND_WT OUT
date -u > $OUT/step3-start.txt
$OUT/row.sh aggro 15 740001 || exit 1
for SEED in 740001 750001; do for st in 15 25 100; do for o in $OPPS; do echo $o $st $SEED; done; done; done \
  | grep -vx 'aggro 15 740001' | xargs -P 10 -L 1 $OUT/row.sh || exit 1
date -u > $OUT/step3-end.txt
```

**Step 4, match runs** (`--hand-cap 1000` is the default and is written out; the schedule is the default "live Chipzen steps every 20 hands"). Output goes to the `.txt` logs, with no `tee`; only the exit code is seen.
```
set -e
for SEED in 740001 750001; do
 for pair in "base:$BASE_WT" "cand:$CAND_WT"; do
  L=${pair%%:*}; WT=${pair#*:}
  for o in reference september; do
   (cd $WT && $PY tools/match.py --matches 200 --vs $o --hero bot --wire live --sims 5000 --hand-cap 1000 --seed0 $SEED \
      --dump $OUT/match-$L-$o-$SEED.jsonl) > $OUT/match-$L-$o-$SEED.txt 2>&1
  done
 done
done
```

**Step 5, analysis, only after every dump exists. It fails closed.** `paired.py` reports "cannot pair" to stderr through `sys.exit`, so its output is captured with `2>&1`, and nothing is read until the files are checked.
```
[ $(ls $OUT/base-*.json $OUT/cand-*.json | wc -l) = 180 ] && [ $(ls $OUT/match-*.jsonl | wc -l) = 8 ] || { echo "dumps missing"; exit 1; }
for SEED in 740001 750001; do for st in 15 25 100; do for o in $OPPS; do
  $PY $CAND_WT/tools/paired.py $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json > $OUT/paired-$o-$st-$SEED.txt 2>&1 || true
done; done; done
[ $(ls $OUT/paired-*.txt | wc -l) = 90 ] || { echo "paired files missing"; exit 1; }
for f in $OUT/paired-*.txt; do [ $(grep -c '^A - B:' $f) = 1 ] || { echo "cannot pair: $f"; exit 1; }; done   # exactly one A - B line each
[ $(ls $OUT/match-*.txt | wc -l) = 8 ] || { echo "match logs missing"; exit 1; }
for f in $OUT/match-*.txt; do [ $(grep -c '^vs ' $f) = 1 ] || { echo "no result line: $f"; exit 1; }; done    # exactly one vs line each
grep -l 'no metadata' $OUT/paired-*.txt && { echo "no metadata, rerun"; exit 1; }                             # must print nothing
# only now are verdicts read
for st in 15 25 100; do for o in $OPPS; do
  grep -q 'worse$' $OUT/paired-$o-$st-740001.txt && grep -q 'worse$' $OUT/paired-$o-$st-750001.txt && echo "GATE FAIL $o $st"
done; done                                                  # rule 1: any line printed fails the gate
for SEED in 740001 750001; do for o in reference september; do
  c=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-cand-$o-$SEED.txt)
  b=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-base-$o-$SEED.txt)
  echo "$o $SEED drop(cand-base) $($PY -c "print(round($c-$b,1))")"
done; done                                                  # rule 2: fail if below -5 on both seeds for one opponent
$PY $CAND_WT/tools/match.py --compare $OUT/match-cand-reference-740001.jsonl $OUT/match-base-reference-740001.jsonl   # McNemar, reported only; repeat per opponent and seed
```
Rule 3 reads `$OUT/paired-aggro-15-*.txt` and `$OUT/paired-reference-15-*.txt` (their `A - B` lines).

## Timing at `--sims 5000`
Earlier timing was at 2,000 sims. Measured 26 Nov, `--hero bot --wire live`; the bench rows on the baseline engine (main 3751f70, 0.75). The match rows name no commit: `match --wire` exists only from #121, so 3751f70 cannot have run them, and the build they used was not recorded. All measured with another job running on the machine. The 1-minute load average was 4.1 to 5.3 throughout, above 2, so **every figure below is an upper bound**; each also includes about 0.4 s of process start-up, which the scaling multiplies.

| Measurement | Wall time | Load (1 min) |
|---|---|---|
| bench, 45 runs (15 opponents, 3 stacks), 100 pairs each | 90.9 s | 4.7 to 5.3 |
| bench vs reference, 100 bb, 100 pairs | 1.4 s | 4.9 |
| bench vs september, 100 bb, 100 pairs (slowest opponent, about 6 s) | 6.0 s | 4.7 |
| match vs reference, 5 pairs (10 matches) | 5.6 s | 4.3 to 4.1 |
| match vs september, 5 pairs (10 matches) | 14.6 s | 4.1 to 4.2 |

- **Bench grid:** 90.9 s x 20 (100 to 2,000 pairs) is about 30 min per build and seed set, about 2 h for the four.
- **Match runs:** rough, from 5 pairs. About 0.56 s per match against reference and 1.5 s against september, so about 3.7 min and 9.7 min for 400 matches each: about 13 min per build and seed set, about 54 min for the four.
- **Whole record, serial:** about 3 h upper bound. No stack-depth effect showed in the grid.
- Timing rows are logged in `results/eval-log.xlsx` (Timing sheet).

## Checklist section 6
- [x] Decision rule and exact commands committed before any run (this file)
- [x] `results/<date>-<slug>.md` for the gate results: `results/2026-11-26-phase-c-gate.md`
- [x] Timing rows added to `results/eval-log.xlsx`; run rows follow the runs
- [ ] Vault status line: left to the lead
