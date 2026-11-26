# Bench opponent knobs: paired baseline (#77)

A baseline, not a gate. The bot (`--hero bot`, 2,000 sims per decision) plays `knobs` at 100 bb: the real engine at 500 sims whose settings (realization scale, bluffing, memory, preflop realization) are drawn per hand pair, with a fresh engine per hand. Hands are dealt in duplicate pairs, so 4,000 hands is 2,000 pairs and the interval is a paired one. Seed 920001 is used only here. Build: the commit that adds the opponent.

## Command

```
PYTHONPATH=chipzen python tools/bench.py --hero bot --vs knobs --stack 100 --hands 4000 --sims 2000 --seed0 920001 --dump knobs.json
```

## Result (verbatim)

```
vs knobs                        +13.5 bb/100   95% CI [-10.0, +37.1]     4000 hands   inconclusive
```

The run reports `coerced 0`. The row is in `results/eval-log.xlsx`, experiment `bench-opponent-77`.
