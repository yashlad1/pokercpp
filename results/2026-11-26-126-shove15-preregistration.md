# #126 pre-registration: the shove-15 candidate

Date: 2026-11-26. Issue #126. This record is committed before any gate run. It states the rule, the seeds, the runs and the exact commands. Nothing below was run for a result.

## Candidate
- **Change:** in `chipzen/decide.h` line 218, `if (stackInBB <= 10.0 && equity >= 0.55)` becomes `15.0`. Nothing else.
- **Where it lives:** a fresh local branch cut as one commit on 5423b90, changing only line 218 of `chipzen/decide.h`. Never pushed, never shipped (the owner's call: this candidate never ships, whatever the result). The earlier exploratory branch `exp/shove-15` is on a pre-deslop base and is not reused.
- **Pins not changed.** The tests that encode 10 bb (the boundary tests in `test_decide_constants`, the short-stack pins in `test_solver`) are left as they are, because the candidate never merges. They may fail on the candidate build; the gate does not run them.
- **Baseline:** commit **5423b90** (main after the deslop merge), in its own worktree, with `kPreflopRealization = 0.75` and the shove line at 10.0. The #126 term says "main after the Phase C ship decision"; the owner has not decided, so this record fixes the 0.75 baseline at that named SHA. If 0.85 ships later, the shove result must be re-checked on the 0.85 main with fresh seeds before any ship decision.
- **Order:** runs only after Phase C's C3 runs finish. Both rules change preflop play at 15 bb or less, and C3 loads the machine.
- **Engine build:** both engines use `tools/build_engine.sh`'s default, no `--metal` (the CPU path the shipped image runs). Step 2 checks that `meta.impl` reads `cpu` in the first dump of each build.
- **Live bot today:** 0.75 and 10.0. A pass here is recorded only; nothing ships.

## Seeds and looks
- **Gate seeds:** 760001 and 770001. Bench pair k uses seed0 + k, so 760001 to 762000 and 770001 to 772000. Match pair m uses seed0 + m, so 760001 to 760200 and 770001 to 770200.
- **Fresh (checked 26 Nov at the base commit 5423b90).** `grep -rnE '(^|[^0-9])(76|77)00[0-9]{2}([^0-9]|$)' results --include='*.md'` found no match, and the same search over `docs`, `tools`, `chipzen`, `Makefile` and `readme.md` found none. A scan of every cell of every sheet of `results/eval-log.xlsx` (Summary, Experiments, Runs, Matches, Builds, Timing, Hardware, Unpaired history, Live) for the numbers 760001, 770001 and the 7600xx and 7700xx ranges found 0 hits. Neither seed, nor any seed in those ranges, has been used.
- **Looks counted.** The exploratory round (seeds 810001 and 820001, `results/2026-11-26-exploratory-e1-e4.md`) looked at shove-12 and shove-15 among about 70 rows with unadjusted intervals. shove-12 was identical to base everywhere (the rule never fired). Only shove-15 is gated here. Its exploratory numbers are quoted below; the intervals in this gate are unadjusted 95% intervals.

## Runs
- **Bench, per build and seed set:** reference, nit, station, aggro, maniac and september, at 15, 25 and 100 bb. That is 18 runs. Each is 2,000 seat-swapped pairs (`--hands 4000`), `--hero bot --wire live --sims 5000`.
- **Match, per build and seed set:** reference and september, 200 pairs each (400 matches: every pair is played twice with the seats swapped), `--hand-cap 1000`, the default schedule, `--hero bot --wire live --sims 5000`. In a 100 bb rising-blind match the rule only fires in late levels, so the effect is diluted (the #126 term).
- **Blind schedule:** the default, "live Chipzen steps every 20 hands" (`blinds_for` in `tools/match.py`). 100 bb stack, first big blind 100, stepping 100, 150, 200, 300, 400, 600, 800 every 20 hands, no antes. Levels past hand 140 are extrapolated, never seen live. At the hand cap the agent seated first wins on level chips.
- **Totals:** 72 bench dumps (18 runs x 2 builds x 2 seeds) and 8 match dumps.
- **Cost:** about 40% of C3's grid; C3's measured wall time is in its gate record.

## Decision rules (fixed now)
Every comparison is candidate minus baseline on the same deals. The commands pass the candidate dump first, so `tools/paired.py`'s `A - B` line is candidate minus baseline. In that script the verdict word is `better` when the 95% interval is entirely above 0, `worse` when entirely below 0, else `inconclusive`.

1. **Bench harm.** A row is one (opponent, stack) pair. A row fails when its paired `A - B` interval is entirely below 0 (`worse`) on both seed sets. Any failing row parks the candidate. The record lists every row that fails, and every row that is `worse` on one set only.
2. **Match harm.** Win rate is wins over 400 matches, from the `vs X k/n` line. Drop is candidate win rate minus baseline win rate, in points. Fails if the drop is worse than -5 points on both seed sets, against reference or against september. `match.py --compare` (McNemar) is reported but does not gate.
3. **Benefit (gating).** Reference, nit and station at 15 bb each have their paired `A - B` interval entirely above 0 (`better`) on both seed sets. All three are required. Each target's interval is reported for both seeds whatever the outcome. The exploratory gains were found among about 70 looks, so expect them to shrink; a fail on one target is still reported and read.
4. **Outcome.** Pass = no fail under rules 1 or 2, and rule 3 holds. A pass is recorded only; nothing ships. A fail parks the candidate with its numbers.
5. **No peeking; fail closed.** No result number is read until all 80 dumps exist (72 bench, 8 match). Step 3's `bench.py` output and step 4's `match.py` output go to log files under `$OUT`, with no `tee`; the person running sees only `IDENTICAL` or `different` and exit codes until then. A crash means the whole set is rerun from step 2. A `paired.py` "no metadata" warning counts as a failed pairing and also means a rerun. Step 5 fails closed: no verdict is read unless all 36 paired files hold exactly one `A - B:` line each and all 8 match logs exactly one `vs ` line each.

**Identity check (changed from C1).** At 15 bb the rule must fire, so an IDENTICAL row at 15 bb (except september) means the candidate did not take; it stops everything. At 25 and 100 bb the rule may never fire (in the exploratory round reference at 25 bb was not identical, so it can), so an IDENTICAL row there is recorded as neutrality and does not stop the run. September rows are unseeded, so two runs differ whatever the candidate does and a september row is never IDENTICAL; the other five opponents carry the check.

## What the rules can and cannot see
- **Exploratory half-widths (95%, paired, shove-15 minus base, 2,000 pairs, live wire, 5,000 sims, seeds 810001 and 820001).** At 15 bb: reference about ±2.7 and ±2.5, nit about ±2.5, station about ±18, aggro about ±12. At 25 bb: reference about ±1.3. These are the sizes this gate's rows should have.
- **Exploratory shove-15 results (E3, diff vs base, bb/100, two seeds).** Reference 15: +5.0 and +5.2, better on both. Nit 15: +6.6 and +6.1, better on both. Station 15: +34.8 and +51.1, better on both. Aggro 15: +8.9 and -2.2, inconclusive. Reference 25: +0.6 and +0.3, neutral. These were picked out of about 70 looks, so they are probably optimistic.
- **Half-widths at 100 bb (C1's figures, same pair count, from #81 and #82 with engine hero and 2,000 sims; the live-wire 5,000-sim widths are not yet measured).** About ±2 to ±4 against reference and ±87 to ±92 against aggro. The 100 bb aggro and maniac rows can only fail on a very large loss, so they test little.
- **Bench harm false-fail rate (no real effect anywhere, normal approximation):** about 2.5% per row per set, so about 0.06% per row on both sets and about 1.1% over 18 rows.
- **Match harm false-fail rate for a build with no real change:** about 1% per opponent, about 2% over the two. At 400 matches and a 50% win rate, a win-rate difference has a standard deviation of about 3.5 points, so a drop over 5 points happens about 8% per set and about 0.6% on both, assuming independent sets.
- **Benefit power.** If the true gain equalled the exploratory estimates, each of reference, nit and station would clear 0 on a set with probability about 96%, 99% and 99%, so about 90% that all three clear on both sets. If the exploratory gains were inflated by selection, the real chance is lower.
- **September is the real, unseeded module** (`pokercpp_engine_base`, built from c057f40 exactly as C1 step 1). The fixed-seed stand-in used by the deslop pins is not used here. September limits, as in C1: (a) The September module cannot be seeded, so september rows are paired on the hero side only. Their intervals will be wider than the half-widths quoted. (b) The identity check cannot fire on september rows, because the two runs differ whatever the candidate does; the other five opponents carry it. (c) The match gate's 3.5-point standard deviation is already the unpaired figure, so its false-fail estimate still holds against september.

## Commands
Each step is a script run with `bash`, so `exit` stops the run. Set these once. The same `$PY` (pybind11, pokerkit and openpyxl installed) is used for every command.

```
PY=<python with pybind11 and pokerkit>
BASE_WT=<worktree of the baseline commit>
CAND_WT=<worktree of the local shove-15 branch, one commit on 5423b90>
OUT=<new empty directory for dumps and logs>
OPPS="reference nit station aggro maniac september"
```

**Step 0, preconditions.** Stops if any check fails.
```
[ "$(git -C $BASE_WT rev-parse --short=7 HEAD)" = 5423b90 ] || { echo "baseline is not 5423b90"; exit 1; }
git -C $CAND_WT diff --stat 5423b90..HEAD                                        # chipzen/decide.h only, 1 line changed
[ "$(git -C $CAND_WT diff --numstat 5423b90..HEAD)" = "$(printf '1\t1\tchipzen/decide.h')" ] || { echo "candidate diff is not the one line"; exit 1; }
git -C $CAND_WT diff -U0 5423b90..HEAD | grep '^[-+] '                           # shows exactly the 10.0 line and the 15.0 line
grep -n 'stackInBB <= ' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h      # 10.0 in the baseline, 15.0 in the candidate
grep -n 'kPreflopRealization =' $BASE_WT/chipzen/decide.h $CAND_WT/chipzen/decide.h   # equal in both (0.75)
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

**Step 3, bench runs, with the identity check inside each row.** A row runs the baseline, then the candidate, then compares the two `results` lists and prints only `IDENTICAL` or `different`, never a number. The `bench.py` output goes to `$OUT/bench-*.log`. Any failing command stops everything, and so does an IDENTICAL row at 15 bb (not september). An IDENTICAL row at 25 or 100 bb is printed and the run continues. The first row (reference, 15 bb, seed 760001) runs alone, so a bad setup stops early. Then the other 15 bb rows (both seeds) run under `xargs -P` with at most 10 jobs and must all finish before the 25 and 100 bb rows start, so a candidate that did not take stops the run before the long grid. Every pair is seeded from seed0 + k, so job order does not change the dumps (the september rows are unseeded either way). The printed rows are saved to `$OUT/step3-rows.txt`.
```
cat > $OUT/row.sh <<'EOS'
#!/bin/bash
set -e; trap 'exit 255' ERR          # any failure makes xargs stop launching new rows
o=$1; st=$2; SEED=$3
for pair in "base:$BASE_WT" "cand:$CAND_WT"; do
  L=${pair%%:*}; WT=${pair#*:}
  (cd $WT && $PY tools/bench.py --hero bot --wire live --sims 5000 --vs $o --stack $st --hands 4000 --seed0 $SEED \
     --dump $OUT/$L-$o-$st-$SEED.json) > $OUT/bench-$L-$o-$st-$SEED.log 2>&1
done
r=$($PY -c "import json,sys; a,b=(json.load(open(p))['results'] for p in sys.argv[1:]); print('IDENTICAL' if a==b else 'different')" $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json)
echo "$o $st $SEED $r"
if [ "$r" = IDENTICAL ] && [ "$st" = 15 ] && [ "$o" != september ]; then exit 255; fi   # the candidate did not take
exit 0
EOS
chmod +x $OUT/row.sh; export PY BASE_WT CAND_WT OUT
date -u > $OUT/step3-start.txt
$OUT/row.sh reference 15 760001 >> $OUT/step3-rows.txt || exit 1
for st in 15 "25 100"; do
  for SEED in 760001 770001; do for s1 in $st; do for o in $OPPS; do echo $o $s1 $SEED; done; done; done \
    | grep -vx 'reference 15 760001' | xargs -P 10 -L 1 $OUT/row.sh >> $OUT/step3-rows.txt || exit 1
done
date -u > $OUT/step3-end.txt
```

**Step 4, match runs** (`--hand-cap 1000` is the default and is written out; the schedule is the default "live Chipzen steps every 20 hands"). Output goes to the `.txt` logs, with no `tee`; only the exit code is seen.
```
set -e
for SEED in 760001 770001; do
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
[ $(ls $OUT/base-*.json $OUT/cand-*.json | wc -l) = 72 ] && [ $(ls $OUT/match-*.jsonl | wc -l) = 8 ] || { echo "dumps missing"; exit 1; }
for SEED in 760001 770001; do for st in 15 25 100; do for o in $OPPS; do
  $PY $CAND_WT/tools/paired.py $OUT/cand-$o-$st-$SEED.json $OUT/base-$o-$st-$SEED.json > $OUT/paired-$o-$st-$SEED.txt 2>&1 || true
done; done; done
[ $(ls $OUT/paired-*.txt | wc -l) = 36 ] || { echo "paired files missing"; exit 1; }
for f in $OUT/paired-*.txt; do [ $(grep -c '^A - B:' $f) = 1 ] || { echo "cannot pair: $f"; exit 1; }; done   # exactly one A - B line each
[ $(ls $OUT/match-*.txt | wc -l) = 8 ] || { echo "match logs missing"; exit 1; }
for f in $OUT/match-*.txt; do [ $(grep -c '^vs ' $f) = 1 ] || { echo "no result line: $f"; exit 1; }; done    # exactly one vs line each
grep -l 'no metadata' $OUT/paired-*.txt && { echo "no metadata, rerun"; exit 1; }                             # must print nothing
# only now are verdicts read
for st in 15 25 100; do for o in $OPPS; do
  grep -q 'worse$' $OUT/paired-$o-$st-760001.txt && grep -q 'worse$' $OUT/paired-$o-$st-770001.txt && echo "GATE FAIL $o $st"
done; done                                                  # rule 1: any line printed fails the gate
for SEED in 760001 770001; do for o in reference september; do
  c=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-cand-$o-$SEED.txt)
  b=$(awk '/^vs /{split($3,a,"/"); print 100*a[1]/a[2]}' $OUT/match-base-$o-$SEED.txt)
  echo "$o $SEED drop(cand-base) $($PY -c "print(round($c-$b,1))")"
done; done                                                  # rule 2: fail if below -5 on both seeds for one opponent
for o in reference station nit; do
  grep -q 'better$' $OUT/paired-$o-15-760001.txt && grep -q 'better$' $OUT/paired-$o-15-770001.txt || echo "BENEFIT MISS $o 15"
done                                                        # rule 3: any line printed fails the benefit check
for SEED in 760001 770001; do for o in reference september; do
  $PY $CAND_WT/tools/match.py --compare $OUT/match-cand-$o-$SEED.jsonl $OUT/match-base-$o-$SEED.jsonl   # McNemar, reported only
done; done
```
Rule 4 then reads: pass means no `GATE FAIL` line, no drop worse than -5 on both seeds for the same opponent, and no `BENEFIT MISS` line.

## Checklist (#126)
- [x] Decision rule and exact commands committed before any run (this file)
- [ ] `results/<date>-<slug>.md` for the gate results: written after the runs, after Phase C's C3 finishes
- [ ] Run rows logged in `results/eval-log.xlsx`: after the runs
- [ ] Vault status line: left to the lead
