# Partial bluffer bench (24 Nov 2026)

**Question:** how does the bot do against an opponent that bluffs only some of the time? Until now the bench had only never-bluffers (reference, nit) and always-bluffers (aggro, maniac).

**Opponent:** `Bluffer(p)` in `tools/bench.py` (`bluff0`, `bluff25`, `bluff50`).
- It plays like reference, except that a share p of its no-pair postflop hands, fixed per deal, bet 0.66 pot (reference's value size) on every street and fold to any bet or raise.
- **Wiring check:** `bluff0` reproduces reference pair for pair. This was checked twice, once by the helper and once by the lead on other seeds.

**Method:** engine hero, 2000 sims, 2000 hands (1000 seat-swapped pairs) per run, at 15 and 100 bb, on seed sets 700001 and 710001. "Diff" is the paired difference vs bluffXX minus vs reference on the same deals, in bb/100. Eval log rows R150 to R157.

| Depth | Seed0 | vs reference | vs bluff25 | Diff, bluff25 | vs bluff50 | Diff, bluff50 |
|---|---|---|---|---|---|---|
| 15 bb | 700001 | +52.8 [+47.0, +58.5] | +51.8 [+45.5, +58.1] | -0.9 [-3.5, +1.6] | +52.3 [+45.1, +59.5] | -0.5 [-4.6, +3.7] |
| 15 bb | 710001 | +51.5 [+46.5, +56.6] | +50.4 [+44.5, +56.4] | -1.1 [-4.2, +2.0] | +46.0 [+39.3, +52.8] | -5.5 [-9.9, -1.1] |
| 100 bb | 700001 | +55.2 [+43.4, +67.0] | +55.8 [+43.2, +68.5] | +0.7 [-3.7, +5.0] | +55.6 [+42.1, +69.2] | +0.4 [-6.1, +7.0] |
| 100 bb | 710001 | +51.5 [+43.8, +59.2] | +53.1 [+43.7, +62.6] | +1.6 [-3.9, +7.1] | +48.6 [+37.9, +59.2] | -2.9 [-10.4, +4.6] |

**Pairs where a bluff changed the result** (the lead's count from the dumps):

| Depth | Seed0 | bluff25: pairs changed | bluff25: bb per changed pair | bluff50: pairs changed | bluff50: bb per changed pair |
|---|---|---|---|---|---|
| 15 bb | 700001 | 46 of 1000 (5%) | -0.41 | 95 (10%) | -0.10 |
| 15 bb | 710001 | 49 (5%) | -0.46 | 107 (11%) | -1.03 |
| 100 bb | 700001 | 62 (6%) | +0.21 | 136 (14%) | +0.06 |
| 100 bb | 710001 | 71 (7%) | +0.46 | 149 (15%) | -0.39 |

**Reading:**
- The bot still beats every bluffer by about 50 bb/100. Only 1 of the 8 paired differences is significant, a small loss (15 bb, bluff50, one seed set), and none is a significant gain.
- **Bluffs are rare here:** they touch 5 to 15% of pairs, because the bluffer folds most hands preflop like reference. The small averages partly reflect that low volume.
- **Where bluffs happen:** the bluffer comes out ahead in about two thirds of the changed pairs, so the bot folds to most bluffs. The net per changed pair is still near zero (-1.0 to +0.5 bb): the bluffer wins small pots when we fold and loses more when we call.
- **Not exploited, not exploiting:** the bot is not badly exploited by this bluffer, but it doesn't exploit the bluffs either.
- **Limit of this test:** a bluffer that also plays loose preflop, like the live match 1 opponent (opened 58% of hands, bet 44% when checked to), would bluff far more often. That is the next opponent to add.
- **Bigger known gap:** against aggro at 15 bb the bot is near break-even (+6.9 [-6.7, +20.6] over 10,000 hands), against about +50 vs reference.
