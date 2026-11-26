# #85 pre-registration: the call-narrowing candidate

Date: 2026-11-26. Issue #85 (child of #53, option built in #84). This record is committed before any gate run. It states the rule, the seeds, the runs and the exact commands. Nothing below was run for a result.

## Candidate
- **Change:** in `chipzen/decide.h`, `constexpr double kCallNarrow = 1.0;` becomes `0.6`. Nothing else.
- **What the option does (from #84).** Each counted call by the opponent multiplies the assumed range by the factor: `range = max(rangeFloor, max(0.05, base * f^c))`, where `base` is the existing raise-based fraction and `c` is the number of counted calls. At `f = 1.0` the range is unchanged for any `c`.
- **What counts as a call.** An opponent `call` of an earlier bet, raise or all-in in the same hand. **Preflop calls of our open count**, so narrowing reaches every postflop decision after a called open. Limps (completing the big blind before any bet), checks and blind posts never count. An `all_in` entry is aggression, not a call.
- **Where it lives:** one fresh commit on 8f11324, changing only that line, on a local branch. Never pushed, never shipped (the owner's call: this candidate never ships, whatever the result). The gate measures only the factor.
- **Baseline:** commit **8f11324**, the head of PR #139 (branch `engine/call-narrow-84`, option off at `kCallNarrow = 1.0`), in its own worktree. With the option off it is byte-identical in play to main (the 83-check pin set, see #139). The baseline therefore carries `kPreflopRealization = 0.75` and the shove line at 10.0, as main does.
- **Order:** runs only after the #126 gate finishes, because both gates load the machine.
- **Engine build:** both engines use `tools/build_engine.sh`'s default, no `--metal` (the CPU path the shipped image runs). Step 2 checks that `meta.impl` reads `cpu` in the first dump of each build.
- **Live bot today:** option off. A pass here is recorded only; nothing ships.

## Seeds and looks
- **Gate seeds:** 780001 and 790001. Bench pair k uses seed0 + k, so 780001 to 782000 and 790001 to 792000. Match pair m uses seed0 + m, so 780001 to 780200 and 790001 to 790200.
- **Fresh (checked 26 Nov at origin/main 9750641).** `grep -rnE '(^|[^0-9])(78|79)00[0-9]{2}([^0-9]|$)' results --include='*.md'` found no match, and the same search over `docs`, `tools`, `chipzen`, `Makefile` and `readme.md` found none. A scan of every cell of every sheet of `results/eval-log.xlsx` (Summary, Experiments, Runs, Matches, Builds, Timing, Hardware, Unpaired history, Live; 20,936 non-empty cells) for the numbers 780001, 790001 and the 7800xx and 7900xx ranges found 0 hits. Neither seed, nor any seed in those ranges, has been used.
- **Looks counted.** One value, 0.6 (from #53), and no earlier look at call narrowing on any seed. A second factor value would be a new look and need fresh seeds. The intervals in this gate are unadjusted 95% intervals.

## Runs
- **Bench, per build and seed set:** reference, nit, station, aggro, maniac and september, at 15 and 100 bb. That is 12 runs. Each is 2,000 seat-swapped pairs (`--hands 4000`), `--hero bot --wire live --sims 5000`.
- **Match, per build and seed set:** reference and september, 200 pairs each (400 matches: every pair is played twice with the seats swapped), `--hand-cap 1000`, the default schedule, `--hero bot --wire live --sims 5000`.
- **Blind schedule:** the default, "live Chipzen steps every 20 hands" (`blinds_for` in `tools/match.py`). 100 bb stack, first big blind 100, stepping 100, 150, 200, 300, 400, 600, 800 every 20 hands, no antes. Levels past hand 140 are extrapolated, never seen live. At the hand cap the agent seated first wins on level chips.
- **Totals:** 48 bench dumps (12 runs x 2 builds x 2 seeds), 24 paired files, 8 match dumps.
- **Cost:** 56 dumps against C3's 188, about one third of its grid. C3's measured wall times are in `results/2026-11-26-phase-c-gate.md`: 23 min 13 s for its 180 bench dumps (under `xargs -P 10`, alongside another job) and 50 min 57 s for the 8 serial match dumps. The match part is the same size here, so the wall time is expected to be near an hour, dominated by the match step, not one third of C3's wall time.

## Decision rules (fixed now)
Every comparison is candidate minus baseline on the same deals. The commands pass the candidate dump first, so `tools/paired.py`'s `A - B` line is candidate minus baseline. The verdict word is `better` when the 95% interval is entirely above 0, `worse` when entirely below 0, else `inconclusive`.

1. **Bench harm (as C1).** A row is one (opponent, stack) pair. A row fails when its paired interval is `worse` on both seed sets. Any failing row parks the candidate. The record lists every row that fails, and every row that is `worse` on one set only.
2. **Match harm (as C1).** Win rate is wins over 400 matches, from the `vs X k/n` line. Drop is candidate win rate minus baseline win rate, in points. Fails if the drop is worse than -5 points on both seed sets, against reference or against september. `match.py --compare` (McNemar) is reported but does not gate.
3. **Benefit (gating).** Reference and nit at **100 bb** are each `better` on both seed sets. Both are required. The 15 bb rows for reference and nit are the original target rows but are reported only: at 15 bb few hands reach a postflop decision after a call, so narrowing has little to act on.
4. **Control (reported, does not gate).** Station is expected to be neutral or worse: it calls with any two cards, so narrowing on its calls is wrong. A station row `better` on both seeds is reported as a sign that the mechanism is not what #53 assumes. A station row worse on both seeds fails rule 1 like any row; rule 4 only adds the report when station is better on both.
   A blanket factor may well fail on station. That outcome is itself the finding: narrowing needs an opponent-aware form (#37).
5. **Outcome.** Pass = no fail under rules 1 or 2, and rule 3 holds. A pass is recorded only; nothing ships. A fail parks the candidate with its numbers.
6. **No peeking; fail closed (as C1).** No result number is read until all 48 bench dumps and 8 match dumps exist. Step 4's `bench.py` output and step 5's `match.py` output go to log files under `$OUT`, with no `tee`; the person running sees only `IDENTICAL` or `different` and exit codes until then. A crash means the whole set is rerun from step 2. A `paired.py` "no metadata" warning counts as a failed pairing and also means a rerun. Step 6 fails closed: no verdict is read unless all 24 paired files hold exactly one `A - B:` line each and all 8 match logs exactly one `vs ` line each. **Plus, before any number is read:** `grep -c 'ENGINE FAILED'` over every `bench-*.log` and `match-*.txt` must total 0. The bot logs that line when an engine call raises (for example a stale engine module that lacks the new `villain_calls` argument) and then falls back to check/fold. Any nonzero count means a rerun from step 2.

**Identity rule.** A row whose candidate and baseline `results` lists are identical means the rule never fired on those deals. Station is the one opponent that must trigger it: it never folds, so it calls our bets and narrowing must fire at both stacks. An IDENTICAL **station** row (15 or 100 bb) stops everything, since the candidate did not take. For any other opponent an IDENTICAL row is recorded as "rule never fired" and counted as neutral; it does not stop the run (aggro and maniac re-raise instead of calling, nit rarely calls, and september is unseeded, so its two runs differ whatever the candidate does and its row is never IDENTICAL). A stale engine module would make both builds fall back to check/fold identically, so the station identity stop also catches that case.

## What the rules can and cannot see
- **Half-widths (95%, paired, 2,000 pairs, `--hero bot --wire live --sims 5000`), from C3's 0.85 gate, half of each interval, seeds 740001 and 750001.** These come from a different candidate, so this gate's widths will differ with the size and spread of its own effect; they are the nearest measured live-wire figures.
  - **Reference:** 15 bb about ±1.4 and ±1.8; 100 bb about ±1.5 and ±2.2.
  - **Station:** 15 bb about ±1.7 and ±1.3; 100 bb about ±1.5 and ±1.2.
  - **Nit:** 15 bb about ±2.5 and ±2.4; 100 bb about ±8.1 and ±4.2.
  - **Aggro:** 15 bb about ±16.8 and ±16.4; 100 bb about ±92 and ±88. Aggro and maniac (100 bb about ±46 and ±47) rows can only fail on a very large loss, so they test little.
  - C1 quoted older engine-hero, 2,000-sim widths (reference about ±2 at 15 bb and ±2 to ±4 at 100 bb, aggro ±16 to ±17 at 15 bb); they are only indicative and agree in size.
- **What the benefit rule can detect at 100 bb.** Against reference the half-width is about ±1.5 to ±2.2, so a gain of about 2 to 3 bb/100 is visible. Against nit it is about ±4 to ±8, so only a gain of roughly 8 bb/100 or more shows. A nit miss is therefore not over-read: it can mean a gain too small to see, not no gain.
- **Power:** none is stated. There is no earlier estimate of the effect of call narrowing to base one on.
- **Bench harm false-fail rate (no real effect anywhere, normal approximation):** about 2.5% per row per set, so about 0.06% per row on both sets and about 0.8% over 12 rows.
- **Match harm false-fail rate for a build with no real change:** about 1% per opponent, about 2% over the two. At 400 matches and a 50% win rate, a win-rate difference has a standard deviation of about 3.5 points, so a drop over 5 points happens about 8% per set and about 0.6% on both, assuming independent sets.
- **September is the real, unseeded module** (`pokercpp_engine_base`, built from c057f40 exactly as in C1 step 1). (a) It cannot be seeded, so september rows are paired on the hero side only and their intervals are wider than the half-widths quoted. (b) The identity check cannot fire on september rows. (c) The match gate's 3.5-point standard deviation is already the unpaired figure, so its false-fail estimate still holds against september.

## Commands
Each step is a script run with `bash`, so `exit` stops the run. Steps 4, 5 and 6 are saved as `step4.sh`, `step5.sh` and `step6.sh`. They read `OUT`, `HANDS`, `SIMS`, `MATCHES`, `S1`, `S2`, `PY`, `BASE_WT`, `CAND_WT` and `OPPS` from the environment only, so the block below `export`s them. The same `$PY` (pybind11, pokerkit and openpyxl installed) is used for every command. **`BASE_WT` and `CAND_WT` must be absolute paths**: the provenance check runs from `/`.

```
PY="<python with pybind11 and pokerkit>"
BASE_WT="<absolute path of the worktree of the baseline commit 8f11324>"
CAND_WT="<absolute path of the worktree of the local call-narrow branch, one commit on 8f11324>"
OUT="<new empty directory for dumps and logs>"
OPPS="reference nit station aggro maniac september"
HANDS=4000; SIMS=5000; MATCHES=200; S1=780001; S2=790001
export PY BASE_WT CAND_WT OUT OPPS HANDS SIMS MATCHES S1 S2   # the step scripts read only these; the dry run overrides them in a subshell
```

**Step 0, preconditions.** Stops if any check fails.
```
[ "$(git -C $BASE_WT rev-parse --short=7 HEAD)" = 8f11324 ] || { echo "baseline is not 8f11324"; exit 1; }
git -C $CAND_WT diff --stat 8f11324..HEAD                                        # chipzen/decide.h only, 1 line changed
[ "$(git -C $CAND_WT diff --numstat 8f11324..HEAD)" = "$(printf '1\t1\tchipzen/decide.h')" ] || { echo "candidate diff is not the one line"; exit 1; }
git -C $CAND_WT diff -U0 8f11324..HEAD | grep '^[-+] '                           # shows exactly the 1.0 line and the 0.6 line
grep -n 'kCallNarrow =' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h      # 1.0 in the baseline, 0.6 in the candidate
grep -n 'kPreflopRealization =' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h   # equal in both
grep -n 'stackInBB <= ' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h      # equal in both
for WT in $BASE_WT $CAND_WT; do grep -c -- '--wire' $WT/tools/match.py; done    # both must be 1 or more
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
modpath() { (cd / && PYTHONPATH=$1/chipzen $PY -c "import $2;print($2.__file__)"); }   # run from / so the current directory is not on sys.path
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

**Step 3, dry run (required before the real run).** The same step 4, 5 and 6 scripts with `--hands 40`, `--sims 200`, `--matches 2`, seeds 1 and 2, in a scratch `$OUT` that is deleted afterwards. The values are set inside a subshell, so nothing leaks back and the real values stay in force for steps 4 to 6. Rebuilds are not repeated; the step 1 and 2 engines are reused (the scratch `$OUT` needs no engine copy: the engines load from the worktrees). It checks plumbing only and reads no result. If the station identity stop fires here, it is investigated, not ignored. The `grep -c 'ENGINE FAILED'` total must be 0 at the end of the dry run, so a stale engine module surfaces here and not at step 6. The gate record notes that the dry run was done. The dry run counts only if `DRY RUN STEPS OK` prints AND the ENGINE FAILED count prints 0. A failed step 4 would otherwise look like a pass, because `grep -c` prints 0 when there are no files and `rm` exits 0.
```
( export OUT=$(mktemp -d) HANDS=40 SIMS=200 MATCHES=2 S1=1 S2=2; bash step4.sh && bash step5.sh && bash step6.sh && echo "DRY RUN STEPS OK"; cat $OUT/bench-*.log $OUT/match-*.txt | grep -c 'ENGINE FAILED'; rm -r "$OUT" )   # the count must print 0
```

**Step 4, bench runs, with the identity check inside each row.** A row runs the baseline, then the candidate, then compares the two `results` lists and prints only `IDENTICAL` or `different`, never a number. The `bench.py` output goes to `$OUT/bench-*.log`. Any failing command stops everything, and so does an IDENTICAL **station** row. An IDENTICAL row for another opponent is printed and the run continues. The first row (station, 100 bb, seed 780001) runs alone, so a candidate that did not take stops the run before the grid. The other 23 rows then run under `xargs -P 10` with at most 10 jobs. Every pair is seeded from seed0 + k, so job order does not change the dumps (the september rows are unseeded either way). The printed rows are saved to `$OUT/step4-rows.txt`.
```
cat > $OUT/row.sh <<'EOS'
#!/bin/bash
set -e; trap 'exit 255' ERR          # any failure makes xargs stop launching new rows
o=$1; st=$2; SEED=$3
for pair in "base:$BASE_WT" "cand:$CAND_WT"; do
  L=${pair%%:*}; WT=${pair#*:}
  (cd $WT && $PY tools/bench.py --hero bot --wire live --sims $SIMS --vs $o --stack $st --hands $HANDS --seed0 $SEED \
     --dump $OUT/$L-$o-$st-$SEED.json) > $OUT/bench-$L-$o-$st-$SEED.log 2>&1
done
r=$($PY -c "import json,sys; a,b=(json.load(open(p))['results'] for p in sys.argv[1:]); print('IDENTICAL' if a==b else 'different')" $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json)
echo "$o $st $SEED $r"
if [ "$r" = IDENTICAL ] && [ "$o" = station ]; then exit 255; fi   # station must call, so the candidate did not take
exit 0
EOS
chmod +x $OUT/row.sh; export PY BASE_WT CAND_WT OUT HANDS SIMS   # row.sh is launched by xargs, so these must be exported
echo "run: S1=$S1 S2=$S2 HANDS=$HANDS"                      # not a result; shows which run this is
date -u > $OUT/step4-start.txt
$OUT/row.sh station 100 $S1 >> $OUT/step4-rows.txt || exit 1
for SEED in $S1 $S2; do for st in 15 100; do for o in $OPPS; do echo $o $st $SEED; done; done; done \
  | grep -vx "station 100 $S1" | xargs -P 10 -L 1 $OUT/row.sh >> $OUT/step4-rows.txt || exit 1
date -u > $OUT/step4-end.txt
```

**Step 5, match runs** (`--hand-cap 1000` is the default and is written out; the schedule is the default "live Chipzen steps every 20 hands"). Output goes to the `.txt` logs, with no `tee`; only the exit code is seen.
```
set -e
for SEED in $S1 $S2; do
 for pair in "base:$BASE_WT" "cand:$CAND_WT"; do
  L=${pair%%:*}; WT=${pair#*:}
  for o in reference september; do
   (cd $WT && $PY tools/match.py --matches $MATCHES --vs $o --hero bot --wire live --sims $SIMS --hand-cap 1000 --seed0 $SEED \
      --dump $OUT/match-$L-$o-$SEED.jsonl) > $OUT/match-$L-$o-$SEED.txt 2>&1
  done
 done
done
```

**Step 6, analysis, only after every dump exists. It fails closed.** `paired.py` reports "cannot pair" to stderr through `sys.exit`, so its output is captured with `2>&1`, and nothing is read until the files are checked.
```
[ $(ls $OUT/base-*.json $OUT/cand-*.json | wc -l) = 48 ] && [ $(ls $OUT/match-*.jsonl | wc -l) = 8 ] || { echo "dumps missing"; exit 1; }
[ "$(cat $OUT/bench-*.log $OUT/match-*.txt | grep -c 'ENGINE FAILED')" = 0 ] || { echo "ENGINE FAILED seen, rerun from step 2"; exit 1; }
for SEED in $S1 $S2; do for st in 15 100; do for o in $OPPS; do
  $PY $CAND_WT/tools/paired.py $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json > $OUT/paired-$o-$st-$SEED.txt 2>&1 || true
done; done; done
[ $(ls $OUT/paired-*.txt | wc -l) = 24 ] || { echo "paired files missing"; exit 1; }
for f in $OUT/paired-*.txt; do [ $(grep -c '^A - B:' $f) = 1 ] || { echo "cannot pair: $f"; exit 1; }; done   # exactly one A - B line each
[ $(ls $OUT/match-*.txt | wc -l) = 8 ] || { echo "match logs missing"; exit 1; }
for f in $OUT/match-*.txt; do [ $(grep -c '^vs ' $f) = 1 ] || { echo "no result line: $f"; exit 1; }; done    # exactly one vs line each
grep -l 'no metadata' $OUT/paired-*.txt && { echo "no metadata, rerun"; exit 1; }                             # must print nothing
# only now are verdicts read
for st in 15 100; do for o in $OPPS; do
  grep -q 'worse$' $OUT/paired-$o-$st-$S1.txt && grep -q 'worse$' $OUT/paired-$o-$st-$S2.txt && echo "GATE FAIL $o $st"
done; done                                                  # rule 1: any line printed fails the gate
for SEED in $S1 $S2; do for o in reference september; do
  c=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-cand-$o-$SEED.txt)
  b=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-base-$o-$SEED.txt)
  echo "$o $SEED drop(cand-base) $($PY -c "print(round($c-$b,1))")"
done; done                                                  # rule 2: fail if below -5 on both seeds for one opponent
for o in reference nit; do
  grep -q 'better$' $OUT/paired-$o-100-$S1.txt && grep -q 'better$' $OUT/paired-$o-100-$S2.txt || echo "BENEFIT MISS $o 100"
done                                                        # rule 3: any line printed fails the benefit check
for st in 15 100; do
  grep -q 'better$' $OUT/paired-station-$st-$S1.txt && grep -q 'better$' $OUT/paired-station-$st-$S2.txt && echo "CONTROL station $st better on both"
done                                                        # rule 4: reported only
for SEED in $S1 $S2; do for o in reference nit; do
  echo "target $o 15 $SEED: $(grep '^A - B:' $OUT/paired-$o-15-$SEED.txt)"
done; done                                                  # 15 bb target rows: reported only
for SEED in $S1 $S2; do for o in reference september; do
  $PY $CAND_WT/tools/match.py --compare $OUT/match-cand-$o-$SEED.jsonl $OUT/match-base-$o-$SEED.jsonl   # McNemar, reported only
done; done
```
Rule 5 then reads: pass means no `GATE FAIL` line, no drop worse than -5 on both seeds for the same opponent, and no `BENEFIT MISS` line.

## Checklist (#85)
- [x] Decision rule and exact commands committed before any run (this file)
- [ ] `results/<date>-<slug>.md` for the gate results: written after the runs, after the #126 gate finishes
- [ ] Dry run done and noted in the gate record
- [ ] Run rows logged in `results/eval-log.xlsx`: after the runs
- [ ] Vault status line: left to the lead
