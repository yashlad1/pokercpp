# Bench opponents threebet and sizer: paired baseline (#74, #75)

A baseline, not a gate. The bot (`--hero bot`, 2,000 sims per decision) plays each new opponent at 100 bb. Hands are dealt in duplicate pairs, so 4,000 hands is 2,000 pairs and the interval is a paired one. Seed 900001 is used only here. Build: the commit that adds the two opponents.

## Commands

```
PYTHONPATH=chipzen python tools/bench.py --hero bot --vs threebet --stack 100 --hands 4000 --sims 2000 --seed0 900001 --dump threebet.json
PYTHONPATH=chipzen python tools/bench.py --hero bot --vs sizer --stack 100 --hands 4000 --sims 2000 --seed0 900001 --dump sizer.json
```

## Results (verbatim)

```
vs threebet                     +41.1 bb/100   95% CI [+28.0, +54.1]     4000 hands   wins
vs sizer                        +67.1 bb/100   95% CI [+42.5, +91.8]     4000 hands   wins
```

Both runs report `coerced 0`. Rows are in `results/eval-log.xlsx`, experiment `bench-opponents-74-75`, runs R584 and R585.
