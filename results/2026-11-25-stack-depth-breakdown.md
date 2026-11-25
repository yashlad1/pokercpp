# Stack-depth breakdown (25 Nov 2026)

**Question:** how does today's bot do at 10, 15, 25, 50 and 100 bb against each bench opponent? (#80, parent #17.)

**Method:** engine hero (matches `--hero bot` per the parity test), `tools/bench.py --stack N`, 2000 sims, 2000 hands (1000 seat-swapped pairs) per cell, seed0 700001, one dump per run. Apple M4, CPU Monte Carlo, 4 runs in parallel; each run took 5 to 26 s, all 40 runs 121 s wall. Build is origin/main at dec4c2b. Eval log rows R190 to R229, experiment "stack-depth breakdown", logged as single runs.

bb/100 with 95% interval:

| Depth | reference | nit | station | aggro | maniac | loosepassive | loosebluff0 | loosebluff50 |
|---|---|---|---|---|---|---|---|---|
| 10 bb | +56.1 [+51.7, +60.4] | +61.9 [+58.4, +65.3] | +130.7 [+118.0, +143.5] | +8.5 [-13.1, +30.1] | +37.5 [+15.7, +59.3] | +5.1 [-3.1, +13.3] | +66.1 [+50.5, +81.7] | +53.9 [+38.0, +69.9] |
| 15 bb | +52.8 [+47.0, +58.5] | +53.2 [+49.1, +57.3] | +176.6 [+154.9, +198.4] | +13.6 [-16.4, +43.6] | +80.5 [+48.2, +112.7] | +176.6 [+154.9, +198.4] | +29.3 [+19.0, +39.6] | +25.4 [+11.7, +39.0] |
| 25 bb | +50.8 [+43.4, +58.2] | +56.5 [+48.7, +64.3] | +222.6 [+194.6, +250.6] | +53.2 [+5.1, +101.3] | +159.5 [+104.9, +214.1] | +222.6 [+194.6, +250.6] | +35.0 [+23.7, +46.2] | +35.5 [+19.7, +51.3] |
| 50 bb | +53.9 [+43.5, +64.3] | +64.0 [+49.3, +78.7] | +254.5 [+221.2, +287.8] | +231.9 [+146.3, +317.6] | +349.2 [+238.9, +459.4] | +254.5 [+221.2, +287.8] | +37.3 [+23.9, +50.7] | +37.9 [+20.1, +55.6] |
| 100 bb | +55.2 [+43.4, +67.0] | +71.0 [+52.8, +89.3] | +254.5 [+221.2, +287.8] | +607.7 [+446.1, +769.2] | +749.8 [+531.7, +967.8] | +254.5 [+221.2, +287.8] | +39.8 [+24.1, +55.4] | +40.4 [+20.9, +59.8] |

**Reading:**
- **Positive everywhere:** no cell is negative. The bot wins against all eight opponents at all five depths.
- **10 bb:** weakest. Against aggro (+8.5) and loosepassive (+5.1) the interval includes zero, and maniac is only +37.5.
- **15 bb:** aggro is still near break-even (+13.6, interval includes zero) and loosebluff is at +25 to +29, well below its +40 to +66 elsewhere.
- **25 bb:** aggro rises to +53, but the loose bluffers are lowest here and at 15 bb (+35).
- **50 bb:** the gap closes against aggro (+232) and maniac (+349); the weakest cells are the loose bluffers (+37 to +38), and reference is flat near +54.
- **100 bb:** the gap against aggro and maniac is largest in absolute terms (+608, +750) but also the widest intervals; the weakest cells are again the loose bluffers (+40) and reference (+55).
- **Pattern:** against reference and nit the result is flat across depth (about +50 to +70). Against the loose-aggressive types it climbs steeply with depth, so short stacks are where the bot is least ahead.
- **Check before relying on it:** station and loosepassive give identical numbers at 15, 25, 50 and 100 bb (and station is identical at 50 and 100 bb), which looks like the two opponents act the same against this bot on these deals; not investigated here.
