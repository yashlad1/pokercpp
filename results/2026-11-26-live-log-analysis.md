# Live log analysis, 26 Nov 2026

One section per play session. Later sessions go below as new sections. Scripts and how to rerun them: end of file. Logs: `results/live-logs/2026-11-26_*.log`.

## Session 1 (11:00 to 11:13 ET)

### Summary

| match | opponent | our build | result | hands | note |
|---|---|---|---|---|---|
| 1 | opp-A | commit 3e7421d, main at 0.75; preflop realization inferred as 0.75 from the log, see below | won | 40 | not part of the 0.85 sample |
| 2 | opp-B | 0.85 bot, commit 0eff667 | won | 7 | |
| 3 | opp-B | 0.85 bot, commit 0eff667 | won | 21 | |
| 4 | opp-C | 0.85 bot, commit 0eff667 | lost | 41 | busted on hand 41 |

The 0.85 sample is matches 2 to 4: 69 hands, 2 wins and 1 loss.

### Wire facts

- 0 illegal actions and 0 error lines in all four matches (our own check: chosen action outside `legal=`, or a raise outside the min/max raise).
- Decisions: 148, 25, 75 and 78.
- The log's commit stamp is the checkout's HEAD, not necessarily the engine build. The match 1 build was inferred from the numbers: preflop realized/equity on every preflop decision facing a bet is **0.85 in all 63 decisions of the 0eff667 matches (7, 20, 36) and 0.75 in all 23 decisions of the opp-A match**. `measure.py` prints this (section 4).

### Opponent profiles (the 47fcb67 counts, n shown)

| situation | opp-A (n) | opp-B, 2 matches pooled (n) | opp-C (n) |
|---|---|---|---|
| first_in (opponent is SB) | n=20: limp 20 | n=13: limp 9, raise 4 | n=20: fold 7 (35%), raise 13 (65%) |
| vs_open (our open) | n=8: call 8 | n=6: call 4, raise 2 | n=13: fold 6, call 7 |
| cbet (opponent last preflop aggressor, acts first on flop) | n=0 | n=6: check 4, bet 2 | n=8: bet 8 |
| checked_to (we checked, opponent acts) | n=27: check 19, bet 8 | n=13: check 5, bet 8 | n=11: check 2, bet 9 |
| vs_bet flop | n=16: fold 2, call 14 | n=12: fold 3, call 6, raise 3 | n=5: fold 4, call 1 |
| vs_bet turn | n=16: fold 5, call 11 | n=5: fold 3, call 1, raise 1 | n=1: call 1 |
| vs_bet river | n=10: fold 2, call 7, raise 1 | n=5: fold 1, call 3, raise 1 | n=2: fold 1, call 1 |

All samples are small. opp-C bets often 1 to 1.5 times the pot on the flop (750 into 750, 1,125 into 750).

### The opp-C loss (match 4)

- **Hand 41 (-7,729, match over).** We held 7c2d on 2c 7d Th 4s. Preflop call (range 1.00, equity 0.339). Flop: two pair, range 0.76, equity 0.859, raised to 1,050 after their bet. Turn 4s: they raised to 3,750, we credited a range of 0.32 (equity 0.917) and shoved. They held 7s4h, which turned two pair (sevens and fours) that beat ours. 74o is not in a top-32% list, so the 0.917 was computed against a range that excluded the hand they held.
- **Hand 6 (-5,800).** We held Kh7h on Ks Qs 4s 6c 5c, a pair of kings with a weak kicker. We called flop (range 0.13, equity 0.530) and turn bets (range 0.12, equity 0.606) and bet the river (range 0.12, equity 0.714, raise to 3,300). They held KcTh (same pair, better kicker) and called.
- **Three c-bet folds** (hands 24, 38, 40; 375 chips each, all after calling a preflop raise as big blind and checking the flop): we folded to 750, 1,125 and 1,125 bets with realized equity 0.197 vs 0.333 required, 0.279 vs 0.375, and 0.144 vs 0.375.

### C-bet counterfactual

If the c-bet had not narrowed the range (range stays at its preflop value), the pre-bet equities apply: hand 24 flips from fold to call (0.438 x 0.82 discount = 0.359 against 0.333 required); hand 38 still folds (0.350 vs 0.375) and hand 40 still folds (0.252 vs 0.375). That is 1 of 3 folds, 1,125 chips of pots, over n = 8 c-bets: small.

### Range coverage at showdown

Every hand in all logs where the showdown shows the opponent's cards (n = 59 won, lost and split; chips are our net). The engine's rule (`MonteCarloSimulator::villainCombos`): the fraction counts combos, not classes; hand classes from `montecarlo/preflop_ranks.h` are taken in order until cumulative combos reach round(range x 1326); the class crossing the cut is inside. We use our last decision's `range=` in the hand.

| group | lost, inside (chips) | lost, outside (chips) | split, inside | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| opp-A (n=19) | 4 (-2,071) | 2 (-3,744) | 2 | 9 (+13,802) | 2 (+800) |
| opp-B match 2 (n=4) | 1 (-100) | 0 | 0 | 0 | 3 (+10,020) |
| opp-B match 3 (n=6) | 2 (-2,362) | 1 (-1,224) | 0 | 1 (+7,904) | 2 (+4,412) |
| opp-C (n=5) | 0 | 2 (-13,529) | 1 | 0 | 2 (+1,830) |
| 0.85 pooled (n=15) | 3 (-2,462) | 3 (-14,753) | 1 | 1 (+7,904) | 7 (+16,262) |
| all logs (n=59) | 13 (-17,142) | 10 (-24,963) | 4 | 20 (+53,794) | 12 (+23,475) |

Lost showdowns at 0.85 (hand, credited range, opponent hand, its percentile in the preflop order, chips): match 2 hand 5, 1.00, 3dJd, 56%, -100. Match 3 hand 12, 0.27, 7h5h, 70%, -1,224; hand 13, 0.31, AdJs, 7%, -1,875; hand 18, 0.81, 5sJd, 59%, -487. Match 4 hand 6, 0.12, KcTh, 16%, -5,800; hand 41, 0.32, 7s4h, 88%, -7,729.

How to read it:

1. The comparison is partly true by construction: a postflop-narrowed fraction is compared against a preflop ordering, so a hand like 74o on a 7-4 board can never be inside a narrowed top-32% list.
2. What it supports: the preflop-rank range misses about 40% of shown hands, 10 of 23 lost and 12 of 32 won across all logs. Missing is about as common in wins as in losses.
3. The chip gap (inside about +36.7k net, outside about -1.5k) is confounded, since narrow ranges come from aggression and big pots. It is suggestive only: n = 59 showdowns, 13 + 10 lost and 20 + 12 won.
4. In the 0.85 matches, 3 of 6 lost showdowns were outside the range, and they carry 14,753 of the 17,215 chips lost at showdown.

Selection bias: only hands that reach showdown count.

### Our small-blind first action

| log set | fold | limp | raise | SB hands |
|---|---|---|---|---|
| 24 Nov, 8 logs | 1 (0%) | 112 (47%) | 126 (53%) | 239 |
| 26 Nov opp-A | 0 | 12 (60%) | 8 (40%) | 20 |
| 26 Nov opp-B, match 2 | 0 | 3 (75%) | 1 (25%) | 4 |
| 26 Nov opp-B, match 3 | 0 | 6 (55%) | 5 (45%) | 11 |
| 26 Nov opp-C | 0 | 8 (38%) | 13 (62%) | 21 |
| all | 1 (0%) | 141 (48%) | 153 (52%) | 295 |

The bot almost never folds the small blind: 1 fold in 295 hands.

### Limits

- Six matches and 150 hands at 0.85 (69 in session 1, 81 in session 2): this cannot measure 0.85 against 0.75. It shows 0.85 runs cleanly on the live server (no illegal actions, no errors).
- The opponent counts and showdown tables have small n; the c-bet counterfactual uses n = 8.
- The coverage `range=` is 2 decimals, so hands near the cut are uncertain.

## Session 2 (11:25 to 11:34 ET), three more 0.85 matches

One log file, three matches, all commit 0eff667 (the log version line still says v4.0.1).

### Summary

| match | opponent | our build | result | hands | decisions |
|---|---|---|---|---|---|
| 5 | opp-D | 0.85 bot, commit 0eff667 | lost | 10 | 29 |
| 6 | opp-E | 0.85 bot, commit 0eff667 | won | 29 | 52 |
| 7 | opp-F | 0.85 bot, commit 0eff667 | lost | 42 | 91 |

The 0.85 sample is now matches 2 to 7. **Day total at 0.85: 6 matches, 3 won and 3 lost, 150 hands; too small to compare against 0.75.**

### Wire facts

- 0 illegal actions and 0 error lines in all three matches.
- Preflop realized/equity on decisions facing a bet: 0.85 in 84 of 85 decisions (9, 34, 41 per match). The one exception is match 5 hand 5: we faced an all-in bigger than our stack (to_call 18,507, stack 1,293), where realization is 1.0 by design: the all-in ends the betting, so there is no further street to discount (the bot folded). The same 1.0 case appears in the 24 Nov logs.

### Opponent profiles (n shown)

| situation | opp-D | opp-E | opp-F |
|---|---|---|---|
| first_in (opponent is SB) | n=5: limp 1, raise 4 | n=14: fold 4, raise 10 | n=21: fold 5, limp 3, raise 13 |
| vs_open | n=3: call 3 | n=7: fold 4, call 2, raise 1 | n=9: fold 6, call 2, raise 1 |
| cbet | n=2: bet 2 | n=5: check 1, bet 4 | n=7: check 2, bet 5 |
| checked_to | n=4: bet 4 | n=5: check 1, bet 4 | n=10: check 3, bet 7 |
| vs_bet flop | n=4: fold 3, call 1 | n=4: fold 2, raise 2 | n=4: fold 1, call 3 |

All samples are small.

### The biggest losses

- **Match 5, hand 1 (-8,007, match over on hand 10).** JdJc on 6c 8c 5d 5c 8d, against 7c8h. Preflop raise (equity 0.788). Called the flop (range 0.45, equity 0.732) and the turn (range 0.25, equity 0.730), then raised the river to 6,638 (range 0.25, equity 0.803) and was called. They held 7c8h, a full house, percentile 65%, outside the 0.25 range.
- **Match 5, hand 10 (-2,139).** KsAs on Tc Ad 7c Js Td, against 8c9d. We raised the flop, turn and river at range 0.77 (equity 0.820, 0.795, 0.806). They held 89o (percentile 56%, inside 0.77): a straight draw on the flop that made a jack-high straight (7-8-9-T-J) on the turn. They called all three bets.
- **Match 7, hand 42 (-5,248).** Qd4h on Th 8c 3d Qc, against 3cQs. Flop raise at equity 0.260 (the below-0.30 bluff branch, range 0.62). Turn: we raised to 1,531 with a pair of queens (range 0.62, equity 0.725); they reraised to 5,382; we called at range 0.18 (equity 0.685). They held Q3 (two pair), percentile 55%, outside 0.18.

### Our response to the opponent's flop c-bet, and small blind first action

| match | c-bet n | fold | call | raise | fold facing any flop bet | SB hands | SB fold / limp / raise |
|---|---|---|---|---|---|---|---|
| 5 opp-D | 2 | 2 (100%) | 0 | 0 | 3 of 7 (43%) | 5 | 0 / 2 (40%) / 3 (60%) |
| 6 opp-E | 4 | 2 (50%) | 1 (25%) | 1 (25%) | 3 of 6 (50%) | 15 | 0 / 8 (53%) / 7 (47%) |
| 7 opp-F | 5 | 4 (80%) | 1 (20%) | 0 | 7 of 9 (78%) | 21 | 0 / 12 (57%) / 9 (43%) |

Across all logs the bot folded the small blind 1 time in 336 hands.

### Range coverage at showdown, updated

| group | lost, inside (chips) | lost, outside (chips) | split, inside | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| session 2 (n=9) | 3 (-3,846) | 2 (-13,255) | 0 | 2 (+6,860) | 2 (+6,595) |
| 0.85 pooled, matches 2 to 7 (n=23) | 6 (-6,308) | 5 (-28,008) | 1 | 3 (+14,764) | 8 (+22,857) |
| all logs (n=67) | 16 (-20,988) | 12 (-38,218) | 4 | 22 (+60,654) | 13 (+30,070) |

The same four caveats as in session 1 apply (partly by construction; the range misses about 40% of shown hands, 12 of 28 lost and 13 of 35 won across all logs; the chip gap is confounded; only showdown hands count). In the 0.85 matches 5 of 11 lost showdowns were outside the range and carry 28,008 of the 34,316 chips lost at showdown.

## Session 3 (11:36 to 12:06 ET, commit eb4f96a, 0.85 from main)

Four matches in one log file, all stamped eb4f96a, the current main. Session 3 plays identically to 0eff667 (the bench results matched) and its log carries its own commit. The platform's 20-match limit was reached after these four.

### Summary

| match | opponent | result | hands | decisions |
|---|---|---|---|---|
| 8 | opp-G | lost | 44 | 109 |
| 9 | opp-H | ended early: the opponent timed out; result not in the log | 7 | 10 |
| 10 | opp-I | won | 89 | 217 |
| 11 | opp-J | won | 5 | 20 |

Match 9 has no result line. At the last hand the stacks were 10,550 (us) to 9,450, but the match did not finish, so it is not counted as a win.

**Day total at 0.85: 10 matches (sessions 1 to 3), 5 won, 4 lost, 1 unresolved, 295 hands (150 before session 3, 145 in it); too small to compare against 0.75.**

### Wire facts

- 0 illegal actions and no error lines from our bot in all four matches.
- Match 9: the log's 18 `"is_timeout": true` entries are all seat 1, the opponent: automatic checks in `action_history`. Our seat has none.
- Preflop realized/equity on decisions facing a bet: 0.85 in 111 of 114 (34, 4, 72, 4 per match). The 3 at 1.00 are all in match 8, hands 10, 31 and 33: the opponent shoved 11,030 to 11,339 into our 8,500 to 8,900 stack and we folded. An all-in bigger than our stack ends the betting, so realization is 1.0 by design (as in session 2 match 5 and the 24 Nov logs).
- Those three folds did not change the result. Equity was 0.329, 0.324 and 0.387 against 0.494, 0.492 and 0.491 required, so they fold at 0.85 as well. They cost 100, 150 and 150 chips (the blind, and a small-blind limp each), 400 in all, against a 10,000 start. Hand 44 alone cost 7,149.

### Opponent profiles (n shown)

| situation | opp-G | opp-I | opp-J |
|---|---|---|---|
| first_in (opponent is SB) | n=22: fold 4, limp 11, raise 6, shove 1 | n=44: fold 9, limp 12, raise 23 | n=2: limp 1, raise 1 |
| vs_open | n=10: fold 6, call 3, raise 1 | n=22: fold 15, call 7 | n=3: call 3 |
| cbet | n=2: check 1, bet 1 | n=9: check 9 | n=1: check 1 |
| checked_to | n=17: check 9, bet 8 | n=40: check 36, bet 4 | n=5: check 4, bet 1 |
| vs_bet flop | n=7: fold 2, call 3, raise 2 | n=25: fold 13, call 10, raise 2 | n=1: call 1 |
| vs_bet turn | n=7: fold 4, call 3 | n=14: fold 5, call 9 | n=3: fold 1, call 1, raise 1 |
| vs_bet river | n=2: fold 1, raise 1 | n=17: fold 9, call 8 | n=1: call 1 |

opp-H (match 9): first_in n=3, fold 3; vs_open n=2, fold 2; too few hands for more. opp-I mostly checks and rarely bets (4 of 40 when checked to). All samples are small.

### The biggest losses

- **opp-G hand 44 (-7,149, match over).** We held 3hKc on 6d 9s 3d 6c 5c (two pair, threes and sixes); they held Ac6h, trips. Decisions (range, equity, required):
  - preflop call: 0.53, 0.426, 0.300 (realized 0.362);
  - flop call of a 500 raise: 0.18, 0.547, 0.250;
  - turn check: 0.18, 0.576;
  - river: we bet 1,320 at 0.18 (equity 0.681); they shoved to 11,851 and we called 4,829 at range 0.06, equity 0.370, required 0.338.

  The call cleared the bar by 0.03, against a top-6% range that did not contain A6o (percentile 22%). Outside the credited range.
- **opp-I hand 30 (-7,528).** We held 8c5s on 8h 8s Kh (trips, kicker 5); they held 7h8d (87o, percentile 65%: trips with a better kicker, 7). Decisions:
  - preflop call: 0.45, 0.336, 0.278 (realized 0.285);
  - flop bet (raise 446): 0.45, 0.903;
  - their raise to 1,622: we re-raised to 4,116 at 0.18, equity 0.902 (realized 0.740, required 0.300);
  - their re-raise to 7,190: we called the rest (3,074) at range 0.10, equity 0.900, required 0.204.

  Equity of 0.90 was computed against a top-10% range that excluded 87o. Outside the credited range.
- **opp-I hand 22 (-1,818).** We held 7dKd on 8h 7c 3h 2h Jh; they held Ts8s (pair of eights, percentile 40%). Decisions:
  - preflop call: 0.45, 0.459, 0.278 (realized 0.390);
  - flop raise 446: 0.45, 0.639;
  - turn raise 1,034: 0.45, 0.628;
  - river check: 0.45, 0.356.

  The hand was inside the 0.45 range; they called two raises with a pair of eights and we paid 1,818 over three streets.

### Range coverage at showdown, updated

| group | lost, inside (chips) | lost, outside (chips) | split | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| session 3 (n=36) | 15 (-10,494) | 3 (-15,673) | 3 | 11 (+16,998) | 4 (+3,318) |
| 0.85 pooled, matches 2 to 11 (n=59) | 21 (-16,802) | 8 (-43,681) | 4 | 14 (+31,762) | 12 (+26,175) |
| all logs (n=103) | 31 (-31,482) | 15 (-53,891) | 7 | 33 (+77,652) | 17 (+33,388) |

The same four caveats as in session 1 apply (partly by construction; the range misses about a third of shown hands, 15 of 46 lost and 17 of 50 won across all logs; the chip gap is confounded; only showdown hands count). In session 3, 3 of 18 lost showdowns were outside the range but carry 15,673 of the 26,167 chips lost at showdown (hands 44 and 30 above, plus 996).

This share is partly true by construction: the credited range is narrowest (0.06, 0.10) exactly in the biggest pots, after repeated aggression, and those pots are the biggest losses. The supported reading is that in big pots the credited range collapses to the top preflop hands and misses made hands from weak starting hands (A6o trips, 87o trips), because it ignores the board. That points at the board-aware range work (#27, #37), not at the call threshold.

In the 0.85 matches 8 of 29 lost showdowns were outside and carry 43,681 of the 60,483 chips lost at showdown.

### Our response to the opponent's flop c-bet, and small blind first action

| match | c-bet n | fold | call | raise | fold facing any flop bet | SB hands | SB fold / limp / raise |
|---|---|---|---|---|---|---|---|
| 8 opp-G | 1 | 0 | 1 (100%) | 0 | 4 of 10 (40%) | 22 | 0 / 12 (55%) / 10 (45%) |
| 9 opp-H | 0 | 0 | 0 | 0 | none faced | 4 | 0 / 2 (50%) / 2 (50%) |
| 10 opp-I | 0 | 0 | 0 | 0 | 1 of 5 (20%) | 45 | 0 / 23 (51%) / 22 (49%) |
| 11 opp-J | 0 | 0 | 0 | 0 | none faced | 3 | 0 / 0 / 3 (100%) |

Across all logs the bot folded the small blind 1 time in 410 hands.

## Session 4 (21:50 ET, commit 472d572, 0.85 from main)

Three matches in one log file, all stamped v4.0.1 472d572, the current main. The play is the 0.85 preflop realization (see wire facts).

### Summary

| match | opponent | result | hands (won-lost-split) | decisions |
|---|---|---|---|---|
| 12 | opp-T | lost (busted on hand 44) | 44 (19-24-1) | 143 |
| 13 | opp-U | won (opponent busted on hand 68) | 68 (49-18-1) | 139 |
| 14 | opp-H | ended early: the opponent timed out; result not in the log | 11 (11-0-0) | 13 |

Match 14 has no result line. At the last hand the stacks were 10,850 (us) to 9,150, but the match did not finish, so it is not counted as a win. It is the same opponent as match 9, which also ended on timeouts.

**Day total at 0.85 after session 4: 13 matches (sessions 1 to 4), 6 won, 5 lost, 2 unresolved, 418 hands (295 before session 4, 123 in it); too small to compare against 0.75.**

### Wire facts

- **Engine health: 0 `ENGINE FAILED` lines, 0 tracebacks, 0 fallback lines.** Every decision was answered by the engine.
- 0 illegal actions in all three matches. The only error-like lines are 7 `is_timeout in hand 3` flags in match 14; all 17 `"is_timeout": true` entries in the file are seat 1, the opponent. Our seat has none.
- Preflop realized/equity on decisions facing a bet: 0.85 in 79 of 80 decisions (28, 45, 6 per match; match 13 has the one at 1.00). That one is match 13 hand 54: the opponent raised all-in (999), the call ends the betting, so realization is 1.0 by design, and we folded K5o at equity 0.371 against 0.400 required.

### Opponent profiles (n shown)

| situation | opp-T | opp-U | opp-H |
|---|---|---|---|
| first_in (opponent is SB) | n=22: limp 18, raise 4 | n=34: fold 22, limp 4, raise 7, shove 1 | n=5: fold 5 |
| vs_open | n=8: call 8 | n=8: fold 3, call 5 | n=3: fold 3 |
| cbet | n=1: bet 1 | n=5: check 3, bet 2 | n=0 |
| checked_to | n=18: check 15, bet 3 | n=7: check 5, bet 2 | n=0 |
| vs_bet flop | n=19: fold 7, call 11, raise 1 | n=15: fold 8, call 7 | n=1: fold 1 |
| vs_bet turn | n=13: fold 3, call 8, raise 2 | n=6: fold 3, call 3 | n=0 |
| vs_bet river | n=10: fold 2, call 6, raise 2 | n=12: fold 5, call 7 | n=0 |

All samples are small. opp-T limps 18 of 22 as small blind and calls every open; opp-U folds 22 of 34 as small blind.

### The biggest losses

- **Match 12 hand 35 (-7,747).** We held Ks5s on 2d Kh 7c 9c 7h (two pair, kings and sevens); they held 7dJc, trips. Flop and turn raises at range 1.00 (equity 0.839, 0.823). They raised the river to 3,006; we shoved 10,235 at range 0.45, equity 0.799, required 0.299. 7dJc is percentile 50%, outside the 0.45 range.
- **Match 12 hand 43 (-3,607).** Ad7h on Jh 4h 5s 4c As (two pair, aces and fours); they held 4d8s, trips (percentile 84%). Turn call at range 0.39, equity 0.448, required 0.309; river call of 2,295 at range 0.13, equity 0.697, required 0.318. Outside the credited range.
- **Match 12 hand 25 (-2,153).** 3d6c on 9s 7h Ts 6d 9h; they held Ks8s, a straight (percentile 19% against a range of 0.18, a borderline miss at 2 decimals).
- **Match 12 hand 44 (-1,106, match over).** We held KhTs in the big blind, raised all-in preflop at 906 behind and lost to 6d9d (range 1.00).
- Match 13's largest loss was hand 62 (-1,614, 3c2s against 2c2d on 7d 4h 5s 7h Qd).

### Range coverage at showdown, updated

| group | lost, inside (chips) | lost, outside (chips) | split | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| session 4 (n=39) | 15 (-9,055) | 5 (-15,515) | 2 | 15 (+19,829) | 2 (+2,000) |
| 0.85 pooled, matches 2 to 14 (n=98) | 36 (-25,857) | 13 (-59,196) | 6 | 29 (+51,591) | 14 (+28,175) |
| all logs (n=142) | 46 (-40,537) | 20 (-69,406) | 9 | 48 (+97,481) | 19 (+35,388) |

The same four caveats as in session 3 apply (partly by construction; the range misses about 27% of shown hands, 20 of 66 lost and 19 of 67 won across all logs; the chip gap is confounded; only showdown hands count). In session 4, 5 of 20 lost showdowns were outside the range but carry 15,515 of the 24,570 chips lost at showdown (hands 35, 43 and 25 above carry 13,507). As before, the credited range is narrowest in the biggest pots, so this is partly by construction and points at the board-aware range work (#27, #37), not at the call threshold.

### Our response to the opponent's flop c-bet, and small blind first action

| match | c-bet n | fold | call | raise | fold facing any flop bet | SB hands | SB fold / limp / raise |
|---|---|---|---|---|---|---|---|
| 12 opp-T | 1 | 1 (100%) | 0 | 0 | 4 of 5 (80%) | 22 | 0 / 14 (64%) / 8 (36%) |
| 13 opp-U | 2 | 1 (50%) | 1 (50%) | 0 | 2 of 6 (33%) | 34 | 0 / 26 (76%) / 8 (24%) |
| 14 opp-H | 0 | 0 | 0 | 0 | none faced | 6 | 0 / 3 (50%) / 3 (50%) |

Across all logs the bot folded the small blind 1 time in 472 hands.

## Session 5 (22:25 ET, commit 472d572, 0.85 from main)

Three matches in one log file, all stamped v4.0.1 472d572, ending with "session ended (3 matches played)". Hands are won-lost-split by the round winners list.

### Summary

| match | opponent | result | hands (won-lost-split) | decisions |
|---|---|---|---|---|
| 15 | opp-V | won (opponent busted on hand 61) | 61 (36-24-1) | 185 |
| 16 | opp-W | lost (busted on hand 125) | 125 (61-63-1) | 326 |
| 17 | opp-X | won (opponent busted on hand 3) | 3 (2-1-0) | 9 |

**Day total at 0.85 after session 5: 16 matches (sessions 1 to 5), 8 won, 6 lost, 2 unresolved, 607 hands (418 before session 5, 189 in it); too small to compare against 0.75.**

### Wire facts

- **Engine health: 0 `ENGINE FAILED` lines, 0 tracebacks, 0 fallback lines.**
- 0 illegal actions, 0 error-like lines, and no timeout entries in any of the three matches.
- Preflop realized/equity on decisions facing a bet: 0.85 in all 151 of 151 (36, 112, 3 per match). No all-in-ends-betting case occurred.

### Opponent profiles (n shown)

| situation | opp-V | opp-W | opp-X |
|---|---|---|---|
| first_in (opponent is SB) | n=30: fold 4, limp 24, raise 2 | n=62: fold 12, limp 18, raise 32 | n=1: raise 1 |
| vs_open | n=13: fold 4, call 7, raise 2 | n=29: fold 5, call 21, raise 3 | n=1: call 1 |
| cbet | n=1: check 1 | n=17: check 17 | n=0 |
| checked_to | n=34: check 31, bet 3 | n=53: check 40, bet 13 | n=0 |
| vs_bet flop | n=22: fold 11, call 11 | n=25: fold 11, call 14 | n=1: fold 1 |
| vs_bet turn | n=13: fold 2, call 11 | n=19: fold 10, call 9 | n=0 |
| vs_bet river | n=13: call 12, raise 1 | n=16: fold 8, call 7, raise 1 | n=1: raise 1 |

All samples are small. opp-V limps 24 of 30 as small blind and checks 31 of 34 when checked to; opp-W raises 32 of 62 first-in but checked all 17 times it was the last preflop aggressor and acted first on the flop.

### The biggest losses

- **Match 16 hand 125 (-9,535, match over).** We held 2sQd on 8h Jc 7s Qh (pair of queens); they held 7c3h (percentile 91%, inside the 1.00 range). Preflop call, flop raise to 1,056 at equity 0.298 (the below-0.30 bluff branch), turn all-in at equity 0.781. They called with a pair of sevens and the hand was lost on the river.
- **Match 16 hand 23 (-8,385).** JdJh on Ah 5c 6d Ts 4d; they held 2dAd, a pair of aces. We raised three streets and the river (2,663, equity 0.737), they re-raised to 6,367 and we called 3,704 at range 0.69, equity 0.709, required 0.221. Inside the range (percentile 24%).
- **Match 16 hand 111 (-6,264).** 9cKd on 4h 4s Qc 7s 8h, they held QhAh (two pair). We called a 3-bet, checked flop and turn, and raised the river to 3,564 at equity 0.282 (bluff branch). They called.
- **Match 15 hand 55 (-4,551, our largest loss in a won match).** 9h9d on 4h 6c 2c 5h; they held KhKc (percentile 1%). Preflop call of their 3-bet at range 0.32, equity 0.609; flop raise 1,749 (range 0.45, equity 0.712); turn raise to 4,057 (equity 0.679) and a call.
- Match 16 hands 64 (-4,315, KdTc flush lost to a higher flush, QcKs) and 102 (-4,182, 8hKh against Kc4c two pair).

### Range coverage at showdown, updated

| group | lost, inside (chips) | lost, outside (chips) | split | won, inside (chips) | won, outside (chips) |
|---|---|---|---|---|---|
| session 5 (n=66) | 32 (-56,525) | 1 (-3,229) | 2 | 24 (+34,404) | 7 (+20,936) |
| 0.85 pooled, matches 2 to 17 (n=164) | 68 (-82,382) | 14 (-62,425) | 8 | 53 (+85,995) | 21 (+49,111) |
| all logs (n=208) | 78 (-97,062) | 21 (-72,635) | 11 | 72 (+131,885) | 26 (+56,324) |

The same four caveats as in session 3 apply (partly by construction; the range misses about 23% of shown hands across all logs, 21 of 99 lost and 26 of 98 won; the chip gap is confounded; only showdown hands count). In session 5 only 1 of 33 lost showdowns was outside the range (hand 72, 2c3s, -3,229), a much lower miss rate than in sessions 3 and 4. Its big losses are mostly inside the credited range (hands 125, 23, 111, 55, 64, 102): the opponent hands were credited, and the bot lost anyway, at equities of 0.28 to 0.78.

### Our response to the opponent's flop c-bet, and small blind first action

| match | c-bet n | fold | call | raise | fold facing any flop bet | SB hands | SB fold / limp / raise |
|---|---|---|---|---|---|---|---|
| 15 opp-V | 0 | 0 | 0 | 0 | none counted | 31 | 0 / 18 (58%) / 13 (42%) |
| 16 opp-W | 0 | 0 | 0 | 0 | 7 of 15 (47%) | 63 | 0 / 33 (52%) / 30 (48%) |
| 17 opp-X | 0 | 0 | 0 | 0 | 1 of 2 (50%) | 2 | 0 / 1 (50%) / 1 (50%) |

Across all logs the bot folded the small blind 1 time in 568 hands.

## Chipzen table, about 22:40 ET

A 6-player table, not a heads-up match, so it is outside the day totals above.

- Our uploaded bot finished **1st of 6** ("Won the table") over 82 hands and won the most hands (43).
- Places 2 to 6: opp-P, opp-Q, opp-A, opp-R and opp-S.
- Source: the platform's competition page. A hosted bot leaves no local log, so there is no hand-level analysis.
- Build: 704b5e1 upload (0.85 preflop realization).
- It was a 6-handed table, while the bot was designed heads-up.

## How to reproduce

Run from the repo root (python3 3.10 or newer; no other packages):

- `sh results/2026-11-26-live-scripts/run.sh` runs `analyze.py` on the 24 Nov logs (vs_open 22: fold 5, call 16, raise 1 and 27: fold 24, call 2, shove 1; decisions 193 and 117). Pass log paths to analyze others.
- `python3 -I results/2026-11-26-live-scripts/measure.py results/live-logs/2026-11-2*.log` prints the coverage table, c-bet responses, SB first actions and the preflop realization check.
- `opponent47.py` is a verbatim copy of the `Stats` class at commit 47fcb67 (first comment line says so).
