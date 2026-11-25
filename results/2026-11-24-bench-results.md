# Bench results, 2026-11-24

All numbers are from the local bench. They are measured, not projected. Where a 95% interval crosses zero, the row is marked "inconclusive".

## Method

- **Duplicate dealing.** Every hand is played twice on the same seed with the seats swapped. Card luck cancels, so the interval is narrow.
- **Search.** 2000 simulations per decision.
- **Blinds.** 50/100. A stack of 100 bb is 10000 chips, 15 bb is 1500 chips.
- **Sample.** 2000 hands per row (1000 swapped pairs) unless the row says otherwise.
- **Unit.** bb/100 hands, with a 95% interval in brackets.
- **Columns are separate engine builds.** Each column is one build, run on the same seeds as the others.
- **Scripted opponents.** reference, station (calls everything), nit (plays few hands), maniac (shoves a lot), aggro (raises a lot), loosepassive (calls wide, rarely raises) and random.
- **September build.** The earlier bot, commit c057f40, also used as an opponent.
- **Match mode.** Heads-up freezeouts with rising blinds on an ASSUMED schedule: 100 bb start, blinds doubling every 25 hands, no antes, 1,000-hand cap. Results are match wins with a Wilson 95% interval. Seats are swapped on the same decks, so matches come in pairs.
- **Labels.** "inconclusive" means the interval crosses zero (or crosses 50% for match wins). "loses" means the whole interval is below zero.

## a. Baseline, fix 1, fix 1+2

Fix 1 is the call-ends-betting change in the preflop range read. Fix 2 is the opponent-model change that narrows a shover's range. "Before" is the c057f40 engine.

**100 bb deep**


| Opponent | Before | Fix 1 | Fix 1+2 |
|---|---|---|---|
| reference | +31.1 [+18.0, +44.2] | +25.9 [+11.3, +40.5] | +26.6 [+12.1, +41.0] |
| station | +165.0 [+142.6, +187.4] | +166.5 [+144.1, +188.9] | +167.5 [+144.7, +190.3] |
| nit | +53.2 [+40.1, +66.3] | +52.6 [+39.4, +65.8] | +52.3 [+39.0, +65.5] |
| maniac | +47.5 [-15.0, +110.1] inconclusive | +344.1 [+198.1, +490.1] | +798.1 [+586.6, +1009.6] |
| aggro | +230.5 [+127.4, +333.5] | +252.6 [+149.7, +355.5] | +481.2 [+334.5, +627.9] |
| loosepassive | +169.3 [+146.5, +192.1] | +170.1 [+147.4, +192.8] | +166.6 [+143.7, +189.5] |
| random | +331.3 [+240.8, +421.8] | +322.5 [+227.9, +417.1] | +463.3 [+356.2, +570.5] |

**15 bb deep**

| Opponent | Before | Fix 1 | Fix 1+2 |
|---|---|---|---|
| reference | +33.7 [+26.0, +41.4] | +34.3 [+26.6, +41.9] | +33.3 [+25.7, +40.9] |
| station | +170.5 [+148.7, +192.2] | +171.2 [+149.5, +192.9] | +168.6 [+146.9, +190.4] |
| nit | +48.9 [+44.5, +53.3] | +48.5 [+43.7, +53.3] | +47.6 [+43.0, +52.1] |
| maniac | **-66.2 [-79.1, -53.3] loses** | -8.9 [-34.2, +16.3] inconclusive | +75.3 [+44.3, +106.4] |
| aggro | **-38.6 [-57.6, -19.6] loses** | **-30.1 [-49.8, -10.4] loses** | -9.2 [-36.4, +18.1] inconclusive |
| loosepassive | +174.2 [+152.3, +196.0] | +168.8 [+146.8, +190.9] | +174.9 [+152.9, +196.9] |
| random | +52.0 [+32.8, +71.1] | +47.7 [+28.6, +66.7] | +66.8 [+44.5, +89.0] |

**10,000 hands, 15 bb deep**

| Opponent | Fix 1 | Fix 1+2 |
|---|---|---|
| maniac | **-15.9 [-27.2, -4.6] loses** | +68.9 [+54.9, +82.9] wins |
| aggro | **-39.5 [-48.5, -30.6] loses** | **-16.3 [-28.5, -4.1] loses** |

**Reruns at 15 bb, maniac, 2000 hands:** fix 1 -0.7 [-26.4, +24.9] inconclusive; fix 1+2 +74.2 [+42.8, +105.5].

**Sanity check.** Shipping build vs reference, 100 bb, 2400 hands: +27.9 [+14.6, +41.1]. That sits inside the repo's earlier +22.8 [+7.6, +38.0], so the bench reproduces.

**Verdict.** Fix 1 and fix 2 turn the 15 bb losses to maniac into wins (10,000 hands: +68.9 [+54.9, +82.9]). Aggro at 15 bb improves but still loses at 10,000 hands for fix 1+2. No significant change against reference, station, nit, loosepassive or random.

## b. Fix 3, the small-blind open

Small blind, first in, with equity of at least 0.50 against a random hand: raise to 2.5 bb instead of limping. Same seeds as section a; the "Fix 1+2" column is repeated from there.


| Opponent | Depth | Fix 1+2 | Fix 1+2+3 |
|---|---|---|---|
| reference | 100 | +26.6 [+12.1, +41.0] | +39.3 [+23.0, +55.6] |
| station | 100 | +167.5 [+144.7, +190.3] | +252.8 [+220.1, +285.6] |
| nit | 100 | +52.3 [+39.0, +65.5] | +60.7 [+47.7, +73.6] |
| maniac | 100 | +798.1 [+586.6, +1009.6] | +808.1 [+594.5, +1021.7] |
| aggro | 100 | +481.2 [+334.5, +627.9] | +505.4 [+345.6, +665.2] |
| loosepassive | 100 | +166.6 [+143.7, +189.5] | +259.3 [+226.2, +292.5] |
| random | 100 | +463.3 [+356.2, +570.5] | +392.9 [+290.8, +495.0] |
| reference | 15 | +33.3 [+25.7, +40.9] | +46.5 [+40.7, +52.2] |
| station | 15 | +168.6 [+146.9, +190.4] | +181.7 [+159.8, +203.6] |
| nit | 15 | +47.6 [+43.0, +52.1] | +54.4 [+49.7, +59.1] |
| maniac | 15 | +75.3 [+44.3, +106.4] | +81.4 [+50.3, +112.5] |
| aggro | 15 | -9.2 [-36.4, +18.1] inconclusive | +24.1 [-6.1, +54.2] inconclusive |
| loosepassive | 15 | +174.9 [+152.9, +196.9] | +185.0 [+162.9, +207.1] |
| random | 15 | +66.8 [+44.5, +89.0] | +57.9 [+34.7, +81.2] |
| aggro, 10,000 hands | 15 | **-16.3 [-28.5, -4.1] loses** | +6.9 [-6.7, +20.6] inconclusive |
| maniac, 10,000 hands | 15 | +68.9 [+54.9, +82.9] | +69.2 [+55.2, +83.1] |

Reruns at 15 bb: aggro +20.4 [-10.0, +50.8] inconclusive; reference +48.1 [+42.5, +53.8].

**Verdict.** No significant loss anywhere. Clear gains against station and loosepassive at 100 bb and against reference at 15 bb. Aggro at 15 bb moves from a loss to inconclusive (+6.9 [-6.7, +20.6] over 10,000 hands). Fix 3 was kept as part of v3, but section e shows it costs against the September build.

## c. Fix 4, the solved push/fold table

A solved push/fold table for the small blind's first action, applied at a stack cap of 10, 12 or 15 bb (builds fix4_10, fix4_12, fix4_15). The table itself is sound: 58% of hands pushed at 10 bb and a best-response gain of about 0.0005 bb. It lost to v3 on this bench and is parked on branch `research/pushfold`. It is not merged.

**Key rows**


| Opponent | Depth | v3 | Fix 4 |
|---|---|---|---|
| nit | 10 bb | +62.5 [+59.2, +65.8] | +40.1 [+37.2, +43.1] |
| reference | 10 bb | +55.0 [+50.6, +59.4] | +39.8 [+36.7, +42.8] |
| station | 12 bb | +194.1 [+176.3, +211.9] | +140.4 [+118.7, +162.1] |
| aggro | 12 bb | +26.8 [+1.2, +52.4] | +18.7 [-7.5, +44.8] |

Rerun, nit at 10 bb: v3 +61.1 [+57.8, +64.4], fix 4 +39.4 [+36.6, +42.3].

**Zone sweep, all rows** (119 rows; "not run" where that zone was not benched)


| Depth | Opponent | v3 | Fix 4, cap 10 bb | Fix 4, cap 12 bb | Fix 4, cap 15 bb |
|---|---|---|---|---|---|
| 6 bb | reference | +52.7 [+48.6, +56.8] | +45.3 [+42.0, +48.7] | +45.4 [+42.1, +48.7] | +45.0 [+41.6, +48.3] |
| 6 bb | station | +58.5 [+51.2, +65.8] | +50.5 [+40.6, +60.4] | +51.0 [+41.1, +60.9] | +52.0 [+42.0, +61.9] |
| 6 bb | nit | +57.9 [+54.1, +61.7] | +44.1 [+40.5, +47.8] | +44.4 [+40.8, +48.0] | +44.4 [+40.8, +48.0] |
| 6 bb | maniac | +12.4 [+0.1, +24.7] | +11.2 [-2.0, +24.4] inconclusive | +9.2 [-4.1, +22.4] inconclusive | +10.1 [-3.1, +23.2] inconclusive |
| 6 bb | aggro | +9.8 [-2.4, +22.0] inconclusive | +9.2 [-4.1, +22.4] inconclusive | +11.1 [-2.1, +24.3] inconclusive | +9.1 [-4.2, +22.3] inconclusive |
| 6 bb | loosepassive | +12.2 [+3.0, +21.4] | +31.2 [+24.2, +38.2] | +30.6 [+23.5, +37.7] | +33.0 [+26.0, +40.1] |
| 6 bb | random | +24.7 [+13.3, +36.2] | +31.6 [+20.2, +43.1] | +32.1 [+20.6, +43.6] | +32.1 [+20.6, +43.6] |
| 8 bb | reference | +54.5 [+50.6, +58.4] | +42.0 [+39.1, +44.9] | +42.1 [+39.3, +44.9] | +42.1 [+39.2, +45.0] |
| 8 bb | station | +102.9 [+93.0, +112.7] | +81.2 [+67.1, +95.3] | +79.8 [+65.8, +93.9] | +80.7 [+66.6, +94.7] |
| 8 bb | nit | +59.9 [+56.3, +63.6] | +41.6 [+38.8, +44.4] | +42.0 [+39.1, +44.8] | +41.6 [+38.8, +44.4] |
| 8 bb | maniac | +21.9 [+5.3, +38.6] | +20.1 [+2.3, +37.8] | +20.7 [+3.0, +38.4] | +17.1 [-0.6, +34.9] inconclusive |
| 8 bb | aggro | -9.2 [-26.6, +8.2] inconclusive | -3.8 [-22.0, +14.5] inconclusive | -6.5 [-24.8, +11.9] inconclusive | -5.7 [-24.0, +12.6] inconclusive |
| 8 bb | loosepassive | +7.7 [-0.4, +15.8] inconclusive | +25.1 [+18.5, +31.6] | +24.8 [+18.1, +31.5] | +24.7 [+18.0, +31.5] |
| 8 bb | random | +27.0 [+12.6, +41.4] | +34.9 [+20.5, +49.3] | +35.6 [+21.4, +49.8] | +32.5 [+18.2, +46.9] |
| 10 bb | reference | +55.0 [+50.6, +59.4] | +39.7 [+36.7, +42.8] | +39.8 [+36.7, +42.8] | +39.7 [+36.6, +42.7] |
| 10 bb | station | +143.2 [+130.3, +156.0] | +106.4 [+88.2, +124.7] | +108.3 [+90.0, +126.7] | +111.2 [+93.1, +129.4] |
| 10 bb | nit | +62.5 [+59.2, +65.8] | +39.8 [+36.9, +42.7] | +40.1 [+37.2, +43.1] | +39.4 [+36.6, +42.3] |
| 10 bb | maniac | +31.3 [+9.9, +52.7] | +29.6 [+7.5, +51.8] | +30.7 [+8.5, +52.9] | +32.4 [+10.2, +54.6] |
| 10 bb | aggro | +6.3 [-15.2, +27.9] inconclusive | +2.9 [-19.6, +25.3] inconclusive | +7.8 [-14.4, +30.1] inconclusive | +7.2 [-15.3, +29.6] inconclusive |
| 10 bb | loosepassive | +7.3 [-1.2, +15.8] inconclusive | +23.1 [+16.3, +30.0] | +24.6 [+18.0, +31.3] | +22.7 [+15.9, +29.5] |
| 10 bb | random | +50.1 [+32.6, +67.6] | +44.9 [+26.7, +63.1] | +47.8 [+29.6, +66.0] | +41.1 [+22.9, +59.3] |
| 12 bb | reference | +45.9 [+40.3, +51.5] | not run | +34.2 [+30.2, +38.2] | +35.2 [+31.4, +39.0] |
| 12 bb | station | +194.1 [+176.3, +211.9] | not run | +140.4 [+118.7, +162.1] | +139.0 [+117.5, +160.6] |
| 12 bb | nit | +52.4 [+46.6, +58.1] | not run | +34.5 [+31.5, +37.5] | +34.8 [+31.7, +38.0] |
| 12 bb | maniac | +58.1 [+33.3, +82.9] | not run | +45.2 [+19.1, +71.4] | +43.7 [+17.5, +70.0] |
| 12 bb | aggro | +26.8 [+1.2, +52.4] | not run | +18.7 [-7.5, +44.8] inconclusive | +14.7 [-11.1, +40.5] inconclusive |
| 12 bb | loosepassive | +32.8 [+23.4, +42.1] | not run | +31.2 [+23.1, +39.3] | +30.9 [+22.9, +39.0] |
| 12 bb | random | +65.7 [+46.4, +85.1] | not run | +35.7 [+15.4, +55.9] | +33.4 [+13.4, +53.4] |
| 15 bb | reference | +48.0 [+42.2, +53.8] | not run | not run | +30.0 [+26.3, +33.6] |
| 15 bb | station | +182.1 [+159.9, +204.3] | not run | not run | +139.4 [+113.0, +165.7] |
| 15 bb | nit | +52.7 [+47.4, +57.9] | not run | not run | +30.1 [+26.7, +33.5] |
| 15 bb | maniac | +81.7 [+50.5, +112.9] | not run | not run | +64.7 [+33.0, +96.4] |
| 15 bb | aggro | +28.9 [-1.6, +59.3] inconclusive | not run | not run | +25.0 [-5.7, +55.6] inconclusive |
| 15 bb | loosepassive | +181.4 [+159.4, +203.4] | not run | not run | +109.6 [+85.6, +133.5] |
| 15 bb | random | +56.6 [+33.3, +79.9] | not run | not run | +42.4 [+20.0, +64.9] |

**Verdict.** Fix 4 loses to v3 against nit, reference and station, and gains nothing against aggro or maniac (aggro at 12 bb: +18.7 [-7.5, +44.8] inconclusive). Widening the cap does not help. Parked.

## d. The hybrid push/fold

Shove what the table shoves, otherwise play v3. Cap of 12 or 15 bb (builds hyb_12, hyb_15). The v3 column is repeated from the fix 4 run.


| Depth | Opponent | v3 | Hybrid, cap 12 bb | Hybrid, cap 15 bb |
|---|---|---|---|---|
| 6 bb | reference | +52.7 [+48.6, +56.8] | +58.8 [+55.3, +62.3] | +59.0 [+55.4, +62.5] |
| 6 bb | station | +58.5 [+51.2, +65.8] | +42.1 [+35.1, +49.0] | +44.1 [+37.1, +51.1] |
| 6 bb | nit | +57.9 [+54.1, +61.7] | +62.8 [+59.4, +66.1] | +63.0 [+59.6, +66.3] |
| 6 bb | maniac | +12.4 [+0.1, +24.7] | +10.6 [-2.1, +23.3] inconclusive | +8.8 [-3.9, +21.6] inconclusive |
| 6 bb | aggro | +9.8 [-2.4, +22.0] inconclusive | +8.4 [-4.4, +21.1] inconclusive | +7.3 [-5.5, +20.2] inconclusive |
| 6 bb | loosepassive | +12.2 [+3.0, +21.4] | +22.6 [+14.5, +30.6] | +23.9 [+15.8, +31.9] |
| 6 bb | random | +24.7 [+13.3, +36.2] | +28.4 [+16.3, +40.4] | +27.5 [+15.5, +39.4] |
| 8 bb | reference | +54.5 [+50.6, +58.4] | +60.0 [+56.7, +63.4] | +59.0 [+55.7, +62.4] |
| 8 bb | station | +102.9 [+93.0, +112.7] | +83.5 [+73.4, +93.7] | +83.8 [+73.7, +93.8] |
| 8 bb | nit | +59.9 [+56.3, +63.6] | +65.0 [+62.6, +67.5] | +64.4 [+61.9, +66.9] |
| 8 bb | maniac | +21.9 [+5.3, +38.6] | +20.0 [+2.7, +37.3] | +23.9 [+6.8, +41.0] |
| 8 bb | aggro | -9.2 [-26.6, +8.2] inconclusive | -12.3 [-30.5, +5.9] inconclusive | -11.1 [-29.3, +7.0] inconclusive |
| 8 bb | loosepassive | +7.7 [-0.4, +15.8] inconclusive | +16.8 [+9.2, +24.5] | +17.7 [+10.0, +25.3] |
| 8 bb | random | +27.0 [+12.6, +41.4] | +36.4 [+21.3, +51.4] | +34.6 [+19.7, +49.5] |
| 10 bb | reference | +55.0 [+50.6, +59.4] | +57.4 [+53.6, +61.2] | +57.1 [+53.2, +61.0] |
| 10 bb | station | +143.2 [+130.3, +156.0] | +120.5 [+107.4, +133.6] | +123.1 [+110.2, +136.1] |
| 10 bb | nit | +62.5 [+59.2, +65.8] | +64.1 [+61.7, +66.5] | +63.9 [+61.4, +66.4] |
| 10 bb | maniac | +31.3 [+9.9, +52.7] | +37.0 [+15.5, +58.6] | +36.0 [+14.5, +57.5] |
| 10 bb | aggro | +6.3 [-15.2, +27.9] inconclusive | +4.4 [-18.2, +27.0] inconclusive | +5.0 [-17.7, +27.7] inconclusive |
| 10 bb | loosepassive | +7.3 [-1.2, +15.8] inconclusive | +16.4 [+8.7, +24.2] | +15.8 [+7.9, +23.7] |
| 10 bb | random | +50.1 [+32.6, +67.6] | +53.0 [+34.3, +71.7] | +49.4 [+30.5, +68.3] |
| 12 bb | reference | +45.9 [+40.3, +51.5] | +53.9 [+49.3, +58.5] | +54.9 [+50.3, +59.6] |
| 12 bb | station | +194.1 [+176.3, +211.9] | +160.1 [+140.3, +179.9] | +156.7 [+137.0, +176.5] |
| 12 bb | nit | +52.4 [+46.6, +58.1] | +60.5 [+57.6, +63.5] | +60.0 [+57.0, +63.1] |
| 12 bb | maniac | +58.1 [+33.3, +82.9] | +52.4 [+26.8, +78.0] | +55.6 [+29.8, +81.4] |
| 12 bb | aggro | +26.8 [+1.2, +52.4] | +12.2 [-14.6, +39.0] inconclusive | +11.2 [-15.4, +37.9] inconclusive |
| 12 bb | loosepassive | +32.8 [+23.4, +42.1] | +28.7 [+19.7, +37.7] | +29.2 [+20.5, +38.0] |
| 12 bb | random | +65.7 [+46.4, +85.1] | +43.2 [+22.0, +64.4] | +44.6 [+23.4, +65.7] |
| 15 bb | reference | +48.0 [+42.2, +53.8] | not run | +53.0 [+48.5, +57.5] |
| 15 bb | station | +182.1 [+159.9, +204.3] | not run | +160.6 [+135.0, +186.2] |
| 15 bb | nit | +52.7 [+47.4, +57.9] | not run | +61.5 [+58.6, +64.3] |
| 15 bb | maniac | +81.7 [+50.5, +112.9] | not run | +82.0 [+49.8, +114.1] |
| 15 bb | aggro | +28.9 [-1.6, +59.3] inconclusive | not run | +12.9 [-18.1, +44.0] inconclusive |
| 15 bb | loosepassive | +181.4 [+159.4, +203.4] | not run | +130.2 [+106.9, +153.5] |
| 15 bb | random | +56.6 [+33.3, +79.9] | not run | +63.5 [+39.0, +88.1] |

**Verdict.** Mixed, not adopted. It gains against nit but loses against station at 6 bb (+42.1 [+35.1, +49.0] vs v3 +58.5 [+51.2, +65.8]) and against loosepassive at 15 bb (+130.2 [+106.9, +153.5] vs v3 +181.4). Lesson: shove against players who fold, open small against players who call.

## e. v3 vs the September bot

**Chips, duplicate-dealt**

| Depth | v3 vs september |
|---|---|
| 100 bb | -40.6 [-75.6, -5.6] loses |
| 15 bb | -2.4 [-13.1, +8.4] inconclusive |
| 8 bb | -0.3 [-8.6, +8.0] inconclusive |

Rerun at 100 bb: -39.8 [-77.3, -2.3] loses.

**Match mode** (400 matches)


| Opponent | Match wins | Pairs lost both / split / won both | Avg hands per match |
|---|---|---|---|
| september | 192/400 = 48.0% [43.1%, 52.9%] inconclusive | 31 / 146 / 23 | 43.4 |

**Mirror check** (September vs September, expected near zero): +2.5 bb/100   95% CI [-3.2, +8.2]     2000 hands   inconclusive inconclusive.

**Diagnosis, 100 bb, same decks, September as opponent**

| Build or knob | vs september |
|---|---|
| shipping | -38.8 [-80.6, +2.9] inconclusive |
| no memory | -37.0 [-72.3, -1.7] loses |
| no bluffing | -46.0 [-81.8, -10.1] loses |
| realization x0.85 (tighter) | -44.4 [-88.9, +0.1] inconclusive |
| realization x1.15 (looser) | -29.5 [-66.9, +7.8] inconclusive |
| realization off (x1.33) | -40.9 [-82.9, +1.1] inconclusive |
| Fix 1 only | -0.3 [-21.0, +20.5] inconclusive |
| Fix 1+2 | -0.2 [-17.8, +17.3] inconclusive |

**Verdict.** Fix 1 and fix 1+2 are level with September. Adding fix 3 brings the loss back, and switching opponent memory off or changing realization or bluffing does not remove it. The cause is fix 3's small-blind open. Phase 0 of the next step is to revisit its 0.50 cut and its size against September. At 15 and 8 bb the difference is inconclusive.

## f. Match-mode results available

**v3, 400 matches per opponent**


| Opponent | Match wins | Pairs lost both / split / won both | Avg hands per match |
|---|---|---|---|
| reference | 397/400 = 99.2% [97.8%, 99.7%] | 0 / 3 / 197 | 75.7 |
| station | 388/400 = 97.0% [94.8%, 98.3%] | 0 / 12 / 188 | 32.3 |
| nit | 398/400 = 99.5% [98.2%, 99.9%] | 0 / 2 / 198 | 72.3 |
| maniac | 237/400 = 59.2% [54.4%, 64.0%] | 22 / 119 / 59 | 5.9 |
| aggro | 247/400 = 61.8% [56.9%, 66.4%] | 25 / 103 / 72 | 15.5 |
| loosepassive | 385/400 = 96.2% [93.9%, 97.7%] | 0 / 15 / 185 | 32.2 |
| random | 305/400 = 76.2% [71.8%, 80.2%] | 4 / 87 / 109 | 22.2 |

An earlier 40-match smoke run against maniac read 52.5% [37.5%, 67.1%], inconclusive. A match against a shover is decided by one or two all-ins, so matches are short (about 6 hands against maniac).

**Engine logic fixes, 200 matches per opponent** (builds are explained in section g)


| Build, opponent | Match wins | Pairs lost both / split / won both | Avg hands per match |
|---|---|---|---|
| v3, maniac | 122/200 = 61.0% [54.1%, 67.5%] | 10 / 58 / 32 | 6.8 |
| A1+A2, maniac | 121/200 = 60.5% [53.6%, 67.0%] | 12 / 55 / 33 | 6.9 |
| A1+A2+B, maniac | 121/200 = 60.5% [53.6%, 67.0%] | 11 / 57 / 32 | 6.7 |
| v3, aggro | 128/200 = 64.0% [57.1%, 70.3%] | 11 / 50 / 39 | 15.7 |
| A1+A2, aggro | 125/200 = 62.5% [55.6%, 68.9%] | 15 / 45 / 40 | 16.0 |
| A1+A2+B, aggro | 122/200 = 61.0% [54.1%, 67.5%] | 12 / 54 / 34 | 16.7 |
| v3, september | 93/200 = 46.5% [39.7%, 53.4%] inconclusive | 17 / 73 / 10 | 41.6 |
| A1+A2, september | 93/200 = 46.5% [39.7%, 53.4%] inconclusive | 16 / 75 / 9 | 41.2 |
| A1+A2+B, september | 97/200 = 48.5% [41.7%, 55.4%] inconclusive | 12 / 79 / 9 | 42.3 |

**Verdict.** v3 wins about 96 to 99.5% of matches against reference, station, nit and loosepassive, 76.2% against random, and about 60% against maniac and aggro. Against September it is level (inconclusive). The engine fixes do not change the match picture.

## g. Engine logic fixes

Three defects found in review (see the code audit):

- **A1.** The short-stack shove fired when checked to postflop (100 into a 20 pot).
- **A2.** The small-blind open had no guard for facing only the blind.
- **B.** The opponent's bet size was read against a pot that included the bet, so a pot-size bet never narrowed the range and a half-pot bet widened it.

Columns: v3; "A1+A2" (A1 and A2 applied); "A1+A2+B" (all three).


| Depth | Opponent | v3 | A1+A2 | A1+A2+B |
|---|---|---|---|---|
| 100 bb | reference | +38.9 [+22.6, +55.2] | +43.3 [+29.9, +56.7] | +43.3 [+27.1, +59.5] |
| 100 bb | station | +251.7 [+218.4, +284.9] | +255.7 [+222.9, +288.4] | +251.0 [+218.5, +283.6] |
| 100 bb | nit | +59.7 [+46.7, +72.7] | +60.1 [+47.1, +73.0] | +61.7 [+49.0, +74.5] |
| 100 bb | maniac | +788.0 [+576.4, +999.7] | +738.4 [+525.5, +951.2] | +788.3 [+573.9, +1002.7] |
| 100 bb | aggro | +502.1 [+343.6, +660.6] | +500.6 [+340.6, +660.5] | +510.2 [+354.5, +665.8] |
| 100 bb | loosepassive | +249.7 [+216.6, +282.8] | +258.5 [+225.3, +291.6] | +250.9 [+217.8, +283.9] |
| 100 bb | random | +360.8 [+259.2, +462.5] | +421.5 [+318.7, +524.2] | +411.1 [+312.0, +510.2] |
| 100 bb | september | **-47.1 [-84.5, -9.6] loses** | -23.3 [-62.8, +16.3] inconclusive | -21.8 [-57.8, +14.2] inconclusive |
| 15 bb | reference | +49.2 [+43.7, +54.7] | +48.4 [+43.0, +53.9] | +49.2 [+43.8, +54.5] |
| 15 bb | station | +187.1 [+164.8, +209.4] | +161.9 [+142.4, +181.5] | +163.5 [+144.1, +182.9] |
| 15 bb | nit | +53.6 [+48.9, +58.4] | +54.6 [+49.8, +59.4] | +54.0 [+49.4, +58.5] |
| 15 bb | maniac | +74.2 [+43.3, +105.1] | +76.1 [+45.3, +106.8] | +81.7 [+50.5, +112.9] |
| 15 bb | aggro | +18.1 [-12.4, +48.7] inconclusive | +27.2 [-3.0, +57.5] inconclusive | +38.1 [+7.8, +68.5] |
| 15 bb | loosepassive | +179.5 [+157.5, +201.5] | +161.3 [+141.4, +181.2] | +158.2 [+138.3, +178.1] |
| 15 bb | random | +57.0 [+33.5, +80.6] | +55.5 [+32.2, +78.8] | +62.0 [+39.4, +84.7] |
| 15 bb | september | -5.9 [-17.3, +5.5] inconclusive | -9.3 [-20.7, +2.1] inconclusive | -4.6 [-15.4, +6.2] inconclusive |
| 8 bb | reference | +54.2 [+50.0, +58.3] | +52.7 [+48.7, +56.6] | +54.3 [+50.4, +58.2] |
| 8 bb | station | +104.4 [+94.4, +114.4] | +73.8 [+62.3, +85.3] | +73.2 [+61.7, +84.8] |
| 8 bb | nit | +61.4 [+58.2, +64.6] | +60.0 [+56.6, +63.4] | +58.8 [+55.8, +61.8] |
| 8 bb | maniac | +22.8 [+6.1, +39.5] | +20.6 [+3.9, +37.3] | +23.5 [+6.8, +40.2] |
| 8 bb | aggro | -9.8 [-27.1, +7.5] inconclusive | -8.9 [-26.0, +8.3] inconclusive | -8.4 [-25.7, +8.9] inconclusive |
| 8 bb | loosepassive | +8.1 [+0.0, +16.3] borderline (lower bound +0.0) | +51.6 [+39.5, +63.6] | +50.2 [+38.4, +62.0] |
| 8 bb | random | +33.9 [+19.6, +48.3] | +39.7 [+25.4, +54.0] | +39.4 [+25.3, +53.5] |
| 8 bb | september | -2.4 [-10.8, +6.0] inconclusive | -4.1 [-13.1, +4.9] inconclusive | -1.9 [-10.8, +7.0] inconclusive |

**Verdict.** A1 is a trade-off. At 8 bb it is worse against station (+73.8 [+62.3, +85.3] vs v3 +104.4 [+94.4, +114.4]) and better against loosepassive (+51.6 [+39.5, +63.6] vs v3 +8.1 [+0.0, +16.3]). It was reverted. A2 and B are kept: no row loses, and aggro at 15 bb moves to +38.1 [+7.8, +68.5] with B.

## Open items

- **A2+B confirmation run is pending.** The tables above show A1+A2+B, which still includes A1. The final A2+B build has not been benched on its own.
- **The blind schedule is assumed.** Match-mode results depend on 100 bb start, doubling every 25 hands, no antes. The real schedule is unknown.
- **The bench never busts in chips mode.** Each hand restarts at a fixed stack, so opponent memory runs warm and early-match behaviour is not tested.
- **Fix 3 vs September** is diagnosed but not yet tuned.


## h. Engine logic fixes, final: A2 + B (A1 reverted)

A2 = the small-blind open requires facing less than one big blind. B = the opponent's bet size is read against the pot before the bet. A1 (no shove when checked to at 10 bb or less) was reverted because it is a trade-off, not a fix. Same seeds as section g; 2000 hands per row.

| Opponent, depth | v3 | A2+B |
|---|---|---|
| station, 8 bb | +104.4 [+94.4, +114.4] | +99.1 [+89.2, +109.0] |
| station, 15 bb | +187.1 [+164.8, +209.4] | +180.3 [+158.1, +202.4] |
| loosepassive, 8 bb | +8.1 [+0.0, +16.3] | +7.9 [-0.2, +16.0] inconclusive |
| loosepassive, 15 bb | +179.5 [+157.5, +201.5] | +185.6 [+163.4, +207.8] |
| aggro, 8 bb | -9.8 [-27.1, +7.5] inconclusive | -8.0 [-25.2, +9.2] inconclusive |
| aggro, 15 bb | +18.1 [-12.4, +48.7] inconclusive | +26.4 [-4.2, +57.1] inconclusive |
| reference, 8 bb | +54.2 [+50.0, +58.3] | +55.0 [+51.2, +58.9] |
| reference, 15 bb | +49.2 [+43.7, +54.7] | +50.7 [+45.5, +55.9] |
| nit, 8 bb | +61.4 [+58.2, +64.6] | +62.3 [+59.6, +65.0] |
| nit, 15 bb | +53.6 [+48.9, +58.4] | +54.4 [+50.0, +58.8] |
| september, 8 bb | -2.4 [-10.8, +6.0] inconclusive | -0.7 [-8.8, +7.4] inconclusive |
| september, 15 bb | -5.9 [-17.3, +5.5] inconclusive | +1.6 [-10.5, +13.8] inconclusive |
| september, 100 bb | -47.1 [-84.5, -9.6] loses | -19.9 [-56.4, +16.6] inconclusive |

Verdict: no significant loss anywhere; A2 + B committed. v3's loss to September at 100 bb (about -40 bb/100 over four runs) comes from fix 3's open; tuning it is the next step.

Match-mode baseline for v3 (400 matches each, assumed schedule): reference 99.2% [97.8%, 99.7%], station 97.0% [94.8%, 98.3%], nit 99.5% [98.2%, 99.9%], maniac 59.2% [54.4%, 64.0%], aggro 61.8% [56.9%, 66.4%], loosepassive 96.2% [93.9%, 97.7%], random 76.2% [71.8%, 80.2%].

## Correction: the September regression is not established

- Every v3 vs September chips row above (-40.6, -39.8, -37.0, -38.8, -47.1, plus the spot-split -29.7 and the paired-tool -37.1) used the same 1,000 deal pairs: `--hands 2000`, default seed0 = 1, so seeds 1-1000. The repeats were not independent samples; they re-ran the same deals with fresh Monte Carlo noise. Match mode vs September used seeds 1-200.
- A 10,000-hand rerun on seeds 1-5000 (100 bb, 2,000 sims) gave v3 vs September -6.2 bb/100 [-22.1, +9.7], inconclusive. A near-identical build gave -10.7 [-26.7, +5.3]. On seeds 1-1000, two near-identical builds gave -1.0 [-37.1, +35.0] and -50.9 [-90.1, -11.8]: at that size, unseeded Monte Carlo noise alone can produce a "significant" loss.
- "A 3-bet is credited as an opening range" also failed its test: September re-raised the small-blind open about 20 times in about 2,430 opens, worth -2.5 bb/100 [-6.2, +1.1].
- Consequences:
  - fix 3's open is not tuned on this evidence;
  - the open-on vs open-off question will be settled on fresh seeds (seed0 = 100001), 5,000+ pairs, with seeded Monte Carlo, scored by the paired per-seed difference;
  - the A-only vs A+B comparison above also used one seed set and unseeded Monte Carlo, so B's bench evidence is weak either way. B was kept as a logic fix: the bet size really was read on the wrong scale.
- Also noted: the opponent memory's floor counts postflop bets as raises. It held a credited re-raise range near 0.41 where the step function gives 0.18. This goes with the planned raises-in-the-pot keying.

## i. Fix 3's open, on vs off: fresh seeds, 5,000 pairs, paired

Seeded engine builds (Monte Carlo seeded per decision, so reruns are identical), seed0 = 100001 (not the reused 1-1000), 5,000 pairs = 10,000 hands per row. "Open" = current main (small blind opens 2.5 bb at equity >= 0.50); "off" = the same build with the open disabled. The last column is the paired per-pair difference, open - off, in bb/100.

| Opponent, depth | Open | Off | Open - off (95%) | Verdict |
|---|---|---|---|---|
| september, 100 bb | -16.0 [-31.9, -0.1] | -9.1 [-18.6, +0.3] | -6.9 [-22.9, +9.2] | inconclusive |
| september, 15 bb | +5.8 [+0.5, +11.1] | +1.7 [-1.4, +4.9] | +4.1 [-1.1, +9.2] | inconclusive |
| station, 100 bb | +263.9 [+248.6, +279.3] | +167.4 [+157.4, +177.5] | +96.5 [+86.9, +106.1] | open better |
| loosepassive, 100 bb | +263.9 [+248.6, +279.3] | +167.4 [+157.4, +177.5] | +96.5 [+86.9, +106.1] | open better |
| reference, 15 bb | +52.9 [+50.6, +55.3] | +38.5 [+35.4, +41.6] | +14.4 [+12.1, +16.7] | open better |
| reference, 100 bb | +53.1 [+48.7, +57.6] | +39.5 [+34.3, +44.6] | +13.7 [+10.3, +17.0] | open better |
| nit, 100 bb | +60.2 [+53.8, +66.6] | +50.7 [+45.1, +56.3] | +9.4 [+7.1, +11.8] | open better |
| aggro, 15 bb | +24.0 [+10.3, +37.7] | -9.5 [-21.8, +2.7] | +33.5 [+24.3, +42.8] | open better |
| maniac, 15 bb | +83.0 [+69.0, +97.1] | +82.1 [+68.0, +96.1] | +1.0 [+0.1, +1.8] | open better (barely) |

Match mode vs september (200 pairs, seed0 100001, assumed schedule): open 199/400 = 49.8% [44.9%, 54.6%]; off 201/400 = 50.2% [45.4%, 55.1%].

The station and loosepassive rows are identical to the digit. This is not a mix-up: each chunk's dump carries its own opponent label. With seeded Monte Carlo, and a bot that never bets more than about 2/3 pot at 100 bb, the two opponents act identically (loosepassive only folds to bets above pot).

Verdict: the open clearly helps against six scripted opponents and makes no detectable difference against the September build, in chips or matches. Fix 3 stays; no tuning of the open.
