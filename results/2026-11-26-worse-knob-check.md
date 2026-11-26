# Worse-knob check for the paired tools (issue #7)

Tool validation, not a gate. Nothing ships. Issue #7's done-when has two halves: an A/A run reads 0 (done, `results/2026-11-25-phase-b.md`: 0 discordant of 40) and a clearly worse knob reads clearly negative. This file covers the second half for both paired tools. Build: main at 13f9d89. Seeds 850001 and 860001 (bench pair k uses seed0 + k; match pair m uses seed0 + m); no other seed is used for any number here.

## Expectation, written before running

The worse knob is `--realization-scale 0.5` on the engine hero. It halves realized equity, so the bot folds and gives up far too much.
- **Chips:** vs reference at 100 bb, 2,000 pairs, `--hero engine --sims 2000`. A = knob, B = default, same seed. `tools/paired.py A B` should print `worse` on both seeds.
- **Match:** 200 pairs vs reference per build and seed. `match.py --compare knob default` should show the knob's discordant losses clearly above its wins, McNemar p < 0.05, on both seeds.
- If either report does not read clearly negative, that is a finding about the tools and is reported as is.

## Commands

Chips (per seed S in 850001, 860001):

```
PYTHONPATH=chipzen python tools/bench.py --hands 4000 --vs reference --hero engine --sims 2000 --seed0 S --realization-scale 0.5 --dump knob.json
PYTHONPATH=chipzen python tools/bench.py --hands 4000 --vs reference --hero engine --sims 2000 --seed0 S --dump def.json
python tools/paired.py knob.json def.json
```

Match. `tools/match.py` has no knob flag, so the route was a scratch build: a second detached worktree of the same commit with every factor in `equityRealization` and `kPreflopRealization` in `chipzen/decide.h` scaled by 0.5 (0.75, 0.82, 0.90, 1.00 became 0.375, 0.41, 0.45, 0.50) by a one-off `sed`, never committed. This equals scale 0.5 on every street, as the bench flag does (the river is `min(1, 1.0 * 0.5)`). Both builds run `--hero engine`:

```
PYTHONPATH=chipzen python tools/match.py --matches 200 --vs reference --sims 2000 --seed0 S --hero engine --dump m.json   # run in each build
python tools/match.py --compare knob-m.json default-m.json
```

## Results

Chips (reference, 100 bb, 4,000 hands = 2,000 pairs):

```
A - B: -21.1 bb/100   95% CI [-28.3, -14.0]   worse
A - B: -22.3 bb/100   95% CI [-28.2, -16.4]   worse
```

Match vs reference (200 pairs = 400 matches per build):

```
vs reference: discordant A-only 2, B-only 0, p=0.5000 (McNemar exact), 400 matches
vs reference: discordant A-only 2, B-only 0, p=0.5000 (McNemar exact), 400 matches
```

Per build, vs reference: default won 398 of 400 matches on both seeds (2 splits); the knob won 400 of 400 on both seeds. So the knob has two discordant wins and no losses: the sign is the opposite of the expectation, and neither p-value is below 0.05.

## Supplementary, added after seeing the reference result

The reference opponent is saturated in match mode: even the default loses only 2 of 400, so a worse knob has no room to show. As a post-hoc check on whether `--compare` can read a negative at all, the same two builds and seeds were run vs aggro (chosen because it is a registered opponent the default beats clearly, not selected from several). This is not a substitute for the pre-stated reference run.

```
vs aggro: discordant A-only 0, B-only 274, p=0.0000 (McNemar exact), 400 matches
vs aggro: discordant A-only 0, B-only 244, p=0.0000 (McNemar exact), 400 matches
```

Default won 275 and 246 of 400; the knob won 1 and 2 of 400. Here the knob has no discordant wins and 274 and 244 discordant losses.

## Confirmatory run, pre-stated after the reference run saturated

Confirmatory, pre-stated after the reference run saturated: vs aggro, seeds 870001 and 880001, 200 pairs per build and seed, --hero engine, the same two builds. Expect the knob's discordant losses (B-only) to far exceed its wins (A-only), with McNemar p < 0.05 on both seeds.

Run as pre-stated: same two builds, `--hero engine`, 2000 sims, 200 pairs per build and seed.

```
seed 870001: vs aggro: discordant A-only 2, B-only 254, p=0.0000 (McNemar exact), 400 matches
seed 880001: vs aggro: discordant A-only 0, B-only 257, p=0.0000 (McNemar exact), 400 matches
```

Per build vs aggro: default won 255 and 258 of 400; the knob won 3 and 1 of 400. A-only is the knob's wins, B-only its losses: 2 against 254, and 0 against 257, p < 0.0001 on both seeds. The expectation held.

**Pre-statement timing.** The expectation commit a970be3 is dated 05:56:04-05:00. The first confirmatory dump was created at 05:56:04.689, the same second. The commit completed before the run script started (`git commit && ...`, then the script), so the commit comes first by command order. Accepted as pre-stated on that basis. Next time: commit and push the rule first, and start the run a minute later.

## Conclusion

- **Chips report: passes.** `paired.py` prints `worse` on both seeds, -21.1 and -22.3 bb/100 with intervals clear of zero.
- **Match report vs reference: does not read negative, and this is not tuned away.** The knob scored 400/400 against the default's 398/400. The tool reported that correctly; the test opponent cannot discriminate, because the default already wins nearly every match and the knob wins every one.
- **Match report vs aggro: reads clearly negative on both seeds** (0 wins against 274 and 244 losses, p < 0.0001). So the McNemar tool does detect a clearly worse build when the opponent leaves room.
- **Confirmatory run vs aggro (870001, 880001): reads clearly negative on both seeds, as pre-stated.** The pre-stated reference choice failed because reference is saturated (the default wins about 99%); the aggro run on 850001/860001 was post-hoc, the 870001/880001 run was pre-stated.
- Reading for #7: the chips half is met as written, and the match half is met by the pre-stated confirmatory run vs aggro. The reference result stays on record as a failed first choice for the reason above. This closes #7.

Eval log: experiment `worse-knob-check-7`. Runs R558 and R559 (chips, seeds 850001 and 860001). Matches M051 to M062, each knob row followed by its default row: reference and aggro on 850001 (M051-M054), reference and aggro on 860001 (M055-M058), confirmatory aggro on 870001 (M059-M060) and 880001 (M061-M062). The match rows have no seed0 column value because `evlog.py match --dump` reads bench dumps, not match dumps; the seed is in the Schedule text.
