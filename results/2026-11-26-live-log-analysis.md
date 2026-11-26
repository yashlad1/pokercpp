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
- The log's commit stamp is the checkout's HEAD, not necessarily the engine build. The match 1 build was inferred from the numbers: preflop realized/equity on every preflop decision facing a bet is **0.85 in all 63 decisions of the 0eff667 matches (7, 20, 36) and 0.75 in all 23 decisions of the qwentom match**. `measure.py` prints this (section 4).

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
| Poet match 2 (n=4) | 1 (-100) | 0 | 0 | 0 | 3 (+10,020) |
| Poet match 3 (n=6) | 2 (-2,362) | 1 (-1,224) | 0 | 1 (+7,904) | 2 (+4,412) |
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
| 26 Nov Poet, match 2 | 0 | 3 (75%) | 1 (25%) | 4 |
| 26 Nov Poet, match 3 | 0 | 6 (55%) | 5 (45%) | 11 |
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

## How to reproduce

Run from the repo root (python3 3.10 or newer; no other packages):

- `sh results/2026-11-26-live-scripts/run.sh` runs `analyze.py` on the 24 Nov logs (vs_open 22: fold 5, call 16, raise 1 and 27: fold 24, call 2, shove 1; decisions 193 and 117). Pass log paths to analyze others.
- `python3 -I results/2026-11-26-live-scripts/measure.py results/live-logs/2026-11-2*.log` prints the coverage table, c-bet responses, SB first actions and the preflop realization check.
- `opponent47.py` is a verbatim copy of the `Stats` class at commit 47fcb67 (first comment line says so).
