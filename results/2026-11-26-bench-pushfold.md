# Bench opponent pushfold: paired baseline (#76)

A baseline, not a gate. The bot (`--hero bot`, 2,000 sims per decision) plays the new opponent at 15 bb, where the solved push/fold table applies to every small-blind first action. Hands are dealt in duplicate pairs, so 4,000 hands is 2,000 pairs and the interval is a paired one. Seed 910001 is used only here. Build: the commit that adds the opponent.

## Command

```
PYTHONPATH=chipzen python tools/bench.py --hero bot --vs pushfold --stack 15 --hands 4000 --sims 2000 --seed0 910001 --dump pushfold.json
```

## Result (verbatim)

```
vs pushfold                     +34.5 bb/100   95% CI [+23.1, +45.9]     4000 hands   wins
```

The run reports `coerced 0`. The row is in `results/eval-log.xlsx`, experiment `bench-opponent-76`, run R586.
