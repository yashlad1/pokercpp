# Live log analysis, 27 Nov 2026

Two live matches of the v4.1.0 bot (commit 48dc553, engine 48dc553, preflop realization 0.85, call_narrow 1.0). Logs: `results/live-logs/2026-11-27_152253-live-20261127-152253-1.log` and `results/live-logs/2026-11-27_152455-live-20261127-152455-2.log`. A third log from 15:33 has 0 hands (cut off in the lobby) and is not analysed. Opponent names are replaced by labels (opp-Y is new; opp-Q also played the 26 Nov table). Scripts and how to rerun them: end of file; analyze.py and measure.py are the 26 Nov scripts, unchanged; leaks.py is the 26 Nov leak audit with the log path taken as an argument.

## Summary

| match | opponent | start (ET) | result | hands (won-lost-split) | decisions |
|---|---|---|---|---|---|
| 1 | opp-Y | 15:23 | won (opponent busted on hand 38, 20,000 to 0) | 38 (14-24-0) | 106 |
| 2 | opp-Q | 15:30 | lost (busted on hand 91, 0 to 20,000) | 91 (50-41-0) | 208 |

Both results come from the final stacks and agree with the platform's winners. Day total: 1 won, 1 lost, 129 hands, net 0. Far too small to say anything about v4.1.0 against v4.0.1. Match 1 was won while losing 24 of 38 hands: hand 38 alone won 9,931 (a river shove).

## Wire facts and engine health

- Build line in both logs: `pokercpp v4.1.0 commit=48dc553 engine=48dc553 preflop=0.85 call_narrow=1.0`.
- **0 `ENGINE FAILED`, 0 tracebacks, 0 fallback lines. 0 illegal actions and 0 error-like lines** in both matches. Decision time: median 3 ms, max 11 ms.
- Preflop realized/equity on decisions facing a bet: 0.85 in 37 of 37 (match 1) and 91 of 94 (match 2). The 3 at 1.00 all end the betting: hand 71 (call of an all-in raise, 4,573 to call, equity 0.583, required 0.430), hand 87 (call of an all-in raise, 6,473, equity 0.592, required 0.433) and hand 90 (fold to a 15,242 all-in against our 3,958 stack, equity 0.426, required 0.454).

## Opponent profiles (n shown)

| situation | opp-Y | opp-Q |
|---|---|---|
| first_in (opponent is SB) | n=19: fold 1, limp 6, raise 12 | n=45: fold 11, raise 33, shove 1 |
| vs_open (our open) | n=13: fold 3, call 6, raise 4 | n=25: fold 10, call 8, raise 5, shove 2 |
| cbet | n=9: bet 9 | n=22: check 12, bet 10 |
| checked_to | n=12: check 1, bet 11 | n=33: check 17, bet 16 |
| vs_bet flop | n=11: fold 5, call 4, raise 2 | n=17: fold 13, call 4 |
| vs_bet turn | n=6: fold 2, call 4 | n=7: fold 5, call 2 |
| vs_bet river | n=5: fold 1, call 3, raise 1 | n=4: fold 3, call 1 |

All samples are small. opp-Y bets almost whenever it has the chance (c-bet 9 of 9, bets 11 of 12 when checked to). opp-Q raises 33 of 45 first-in and folds to our postflop bets 21 of 28 times.

## The biggest losses

- **Match 2 hand 87 (-7,473).** 7dAd, preflop raise to 1,000 (equity 0.615), they shoved to 7,473 and we called at range 0.75, equity 0.592, required 0.433 (realization 1.00, the all-in ends the betting). They held 7c6h (percentile 75%, inside the range).
- **Match 2 hand 25 (-5,746).** 4s4c on 9h 7d 7h 7c 2d. We raised preflop (equity 0.583), called their 3-bet and a flop bet of 1,626 (we were the small blind and they led) (range 0.21, equity 0.403, required 0.277), and called the river bet of 2,808 at range 0.08, equity 0.558, required 0.244. They held QdQh (their sevens full of queens beat our sevens full of fours; percentile 1%, inside the 0.08 range).
- **Match 2 hand 71 (-5,323).** 6s6d, raise to 750, they shoved to 5,323, called at range 0.74, equity 0.583 (realization 1.00). They held 3d7s (percentile 91%, a bluff) and made the better hand.
- **Match 2 hand 91 (-3,958, match over).** 6d8d on Qs 8c Qd. Preflop call (equity 0.467), flop: we raised all-in at range 0.76, equity 0.651 over their 496 bet. They held 2cQh (trips).
- **Match 2 hand 76 (-3,763).** 2cTd on 2d 9c 8c 4c 8s (two pair). We called flop (930, range 0.23) and a river bet of 2,083 at range 0.08, equity 0.507, required 0.277. They held 7h7d (two pair, sevens and eights, better than ours).
- **Match 1 hand 8 (-2,622, a won match).** 5c4s on Qd 8c 5d 9c Kc; we called a flop bet and a turn bet of 1,872 at range 0.20, equity 0.417, required 0.357. They held 6hQc (pair of queens).
- Match 1 hand 28 (-1,872): a river bluff of 1,065 at equity 0.109 with 2c8s on 9d 7c Kc 6h Qh, called by 9s3c (pair of nines).

In match 2 the four biggest losses besides hand 91 were all calls (two of preflop all-ins, two of river bets at range 0.08), and in each the opponent's hand was inside our credited range, except hand 71 (3d7s, percentile 91%, a bluff against range 0.74).

## Range coverage at showdown

Same method as 26 Nov (`measure.py`, section 1): opponent hands shown at showdown, our last decision's range, chips are our net. n = 22 showdowns (match 1: 5, match 2: 17), no splits.

| group | lost, inside (chips) | lost, outside (chips) | split | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| opp-Y (n=5) | 1 (-1,872) | 2 (-3,452) | 0 | 2 (+13,295) | 0 |
| opp-Q (n=17) | 6 (-23,810) | 4 (-10,110) | 0 | 4 (+2,380) | 3 (+6,000) |
| 27 Nov pooled (n=22) | 7 (-25,682) | 6 (-13,562) | 0 | 6 (+15,675) | 3 (+6,000) |

The four caveats of the 26 Nov note apply (the comparison is partly true by construction; missing is about as common in wins as losses; the chip gap is confounded; only showdown hands count). Here 6 of 13 lost showdowns were outside the range and carry 13,562 of 39,244 chips lost at showdown. Hand 28 (range 1.00) is inside by definition.

## Our response to the opponent's flop c-bet, and small blind first action

| match | c-bet n | fold | call | raise | fold facing any flop bet | SB hands | SB fold / limp / raise |
|---|---|---|---|---|---|---|---|
| 1 opp-Y | 9 | 4 (44%) | 4 (44%) | 1 (11%) | 8 of 22 (36%) | 19 | 0 / 6 (32%) / 13 (68%) |
| 2 opp-Q | 10 | 5 (50%) | 5 (50%) | 0 | 12 of 23 (52%) | 46 | 0 / 21 (46%) / 25 (54%) |

The bot folded the small blind 0 times in 65 hands.

## Leak metrics for issue 176

Computed with the same code as the 26 Nov verification (committed per-hand definitions; "pot" is the total contributed by both seats at the end of the hand, in big blinds of that hand). Definitions:

- **Big-pot calibration:** showdown hands with pot of more than 20 bb, bucketed by the equity logged at our last decision; "won" counts a split as half.
- **Stack-offs:** hands where the opponent bet or raised postflop (the live wire labels both `raise`), we invested more than 50% of our stack at the start of the hand, and our last decision was not a fold.
- **BB calls against a raise:** we are big blind and the opponent raised preflop; our first response.
- **Small-pot flop folds:** flop decisions facing a bet with the pot before the bet at most 10 bb; fold share and our net in those hands.
- **SB limps:** small-blind hands where our first action was a call, against hands where it was a raise.

| metric | 27 Nov (n) | 26 Nov (n) | direction |
|---|---|---|---|
| Big-pot showdowns, all | 10 hands, 3 won, mean logged equity 0.488 | | |
| equity 0.5 to 0.6 | 4 hands, 0 won, -22,305 (all 4 calls vs opp-Q) | | 4 of 4 lost; no reading at n=4 |
| equity 0.7 to 0.8 | 0 hands | 6 hands, 1 won (17%), -31,590 | no data |
| equity 0.7 and up | 1 hand, won (0.852), +9,931 | 26 hands, 17 won (65%) | no data |
| Stack-offs | 6 hands, 5 won (83%), +20,502 | 16 hands, 7 won (44%), -14,172 | won 5 of 6 vs 7 of 16 on 26 Nov; no reading at n=6 |
| BB calls against a raise | 30 calls, +3,943 (15 folds -2,350; 1 raise +500) | 74 calls, -33,276 | +3,943 over 30 calls vs -33,276 over 74 on 26 Nov; no reading at n=30 |
| Small-pot flop folds | 18 of 41 (44%), -5,003; opp-Y 6 of 19, opp-Q 12 of 22 | 47 of 92 (51%), -11,446 | folded 44% vs 51% on 26 Nov; no reading at n=41 |
| SB limps | 27 limps, -7,734 (5 won, 22 lost); 38 raises, -3,519 | 171 limps, -19,581; 138 raises, +51,601; 0 folds | 27 limps, -7,734 vs 171 limps, -19,581 on 26 Nov; no reading at n=27 |

Reading: with 2 matches and 129 hands none of this is a measurement.

- The stack-off and BB-call figures differ from 26 Nov, but they rest on 6 and 30 hands; one stack-off was a 9,931 win.
- The calibration leak cannot be tested: only 1 big-pot showdown had logged equity of 0.7 or more. The 0.5 to 0.6 bucket lost 4 of 4, all calls against opp-Q: two preflop all-in calls (hands 71 and 87, equity 0.58 and 0.59) and two river calls at range 0.08 (hands 25 and 76).
- Small-pot flop folds are about the same share as 26 Nov (44% against 51%), with opp-Q at 55% and opp-Y at 32%.
- Raises from the small blind also lost money today (-3,519), which they did not on 26 Nov: two preflop all-in call losses (hands 71, 87, -12,796) sit in the raise hands. Those are preflop calls, outside the stack-off definition.

## How to reproduce

From the repo root, with the two 27 Nov logs:

- `sh results/2026-11-26-live-scripts/run.sh results/live-logs/2026-11-27_*.log` runs `analyze.py` (match results, decision counts, opponent stats, biggest losses).
- `python3 -I results/2026-11-26-live-scripts/measure.py results/live-logs/2026-11-27_*.log` prints the coverage table, c-bet responses, SB first actions and the preflop realization check.
- `python3 -I results/2026-11-27-live-scripts/leaks.py 'results/live-logs/2026-11-27_*.log'` prints the leak metrics above (chip flow, calibration, stack-offs, small-pot flop folds, SB limps, BB calls, latency); it builds on `analyze.py`.
