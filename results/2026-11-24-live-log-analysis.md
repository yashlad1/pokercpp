# Live log analysis: four external-API matches (24 Nov 2026)

Matches 1 and 2 are analysed in full below (stage 2). Stage 1 extracted the facts from the raw logs in `results/live-logs/`: 193 and 117 decisions, 0 illegal actions in either. The lead re-checked these claims against the parsed logs: the five biggest match 1 losses and their total, the hand 59, 65, 71, 89 and 90 decision numbers, 13 of 33 calls within 0.03 of the price, 28 of 30 preflop folds facing the 6.2 bb open, and match 2's 73 opponent folds (63 preflop).

## Matches 3 and 4 (v4.0.1), short notes

- **Match 3** (`2026-11-24_224546-live3.log`): won in 22 hands. The v4.0.1 short-stack fix fired once (hand 11: min_raise 9014 > max_raise 5851; the bot raised to 5851, accepted).
- **Match 4** (`2026-11-24_224952-live-20261124-224952.log`): lost in 13 hands, 21 decisions, 0 errors.
  - **The bust (hand 13):** JJ, 3-bet pot. We called a flop bet, a turn bet and the river all-in (6700) on 5c 9d 4d 3s 6c. The credited range was 0.07, equity 0.678 against a 0.338 price.
  - **Why it fits H2/H4:** the range is "top 7% of preflop hands", which ignores what three streets of aggression on a four-to-a-straight board mean.
  - **Limps:** the opponent raised all 3 of our small-blind limps, and we folded each, as against match 1's opponent (section 4).

## Correction to the data limits below

The server does send opponent hole cards. The `round_result` payload carries `showdown` (each seat's `hole_cards`, `hand_rank` and `best_hand`), `stacks`, `payouts` and `deck_reveal`; the SDK's `on_round_result` docstring and conformance fixtures list them. Our logging hook logged only the length of `showdown` (`showdown=2`), so the cards were dropped by us, not withheld. Logging them closes limits (1) and (2).

---


## Stage 2: matches 1 and 2

Seat 0 (us) in both. Match 1 = live.log (lost, 90 hands, -10000 chips). Match 2 = live2.log (won, 95 hands, +10000). "bb-sum" = sum of per-hand nets, each in the bb of its level (blinds rise 100/150/200/300/400 every 20 hands, so bb-sums mix levels). Stats was loaded from `git show research/opp-stats:chipzen/opponent.py`; depth = min(our stack, opp stack)/bb from stage-1 start stacks, chained with history nets.

Data limits that bind everything below: (1) opponent hole cards are never logged, so no range claim can be checked against what they held; (2) the board is logged only in STATE lines for the first 50 decisions, so hands 59, 65, 71, 89, 90 have no board; (3) the decision `extra` column is empty, so bluff bets are inferred as postflop bet with equity < 0.30.

## 1. Opponent profiles (Stats counts)

| situation | Match 1 opp | Match 2 opp |
|---|---|---|
| first_in (opp is SB) | n=45: fold 7 (16%), limp 12 (27%), raise 24 + shove 2 (58%) | n=47: fold 39 (83%), limp 3 (6%), raise 5 (11%) |
| first-in raise size | 24 of 26 at 6.2 bb, 2 at 2.0 bb | 3 at 6.6 bb, 2 at 2.0 bb |
| vs_open (our 2.5 bb open) | n=22: fold 5 (23%), call 16 (73%), raise 1 | n=27: fold 24 (89%), call 2, shove 1 |
| vs_shove | n=2: fold 1, call 1 | n=0 recorded |
| cbet (opp last preflop aggressor, acts first on flop) | n=5: check 3, bet 2 | n=2: check 2 |
| checked_to (we checked, opp acts) | n=16: bet 7 (44%), check 9 | n=7: check 7, bet 0 |
| vs_bet flop (our bet) | n=15: fold 9, call 5, raise 1 | n=10: fold 5, call 5 |
| vs_bet turn | n=7: fold 4, call 3 | n=5: fold 2, call 3 |
| vs_bet river | n=7: fold 2, call 4, raise 1 | n=7: fold 3, call 4 |
| vs_bet all streets | n=29: fold 52%, call 41%, raise 7% | n=22: fold 45%, call 55%, raise 0 |

- **Match 1 profile:** "opens 58% of SB hands, almost always to 6.2 bb; calls 73% of our 2.5 bb opens; postflop bets 44% when checked to, folds about half of our bets." Very loose-aggressive preflop, fit-or-fold afterwards.
- **Match 2 profile:** "folds 83% as SB, folds 89% to our opens, never bets postflop when checked to (0 of 7), never raises our bets, calls about half." Tight-passive.

Bench opponents, measured from their `act()` over all 1326 combos (first-in and vs a 2.5 bb open are identical for each): reference fold 72% / call 25% / raise 3%; nit fold 94% / raise 6%; station and loosepassive call 100%; aggro and maniac raise 100% (aggro to 3x min_raise = 6 bb; maniac shoves). Postflop: reference only bets with two pair or better (board pairs count), folds no-pair hands to any bet; nit bets only with QQ+/TT+ type holdings and folds otherwise; loosepassive never bets or raises.

- **Match 2 opp is closest to nit** on preflop frequencies (fold 83 vs 94, raise 11 vs 6). Mismatches: 3 limps and 2 calls (nit never does either) and 55% postflop calls (nit folds everything but premiums; reference/loosepassive call). Best description: nit preflop, reference-like postflop.
- **Match 1 opp is closest to none.** Its first-in raise rate and 6.2 bb size look like aggro (sizing 6 bb) at 58% instead of 100%; its 73% call of our opens looks like station/loosepassive; its 52% postflop folding is unlike aggro, maniac, station and loosepassive. Nearest single choice by preflop distance: aggro; by calling our opens: loosepassive. Treat it as unmatched.

## 2. Where match 1 was lost

Five biggest losses (stage 1): 59 (-4340), 65 (-4036), 90 (-3932), 71 (-2050), 89 (-1600); sum -15958 against a match total of -10000, so the other 85 hands netted +5958. 60 is next (-1240). Peak stack was 12272 at hand 39; by hand 60 we had 7425, by hand 80 4630. "range" is what the engine credited, "realized" the 0.75/0.82/0.90/1.00 discounted equity, "required" to_call/(pot+to_call).

**Hand 59, Qc7s, bb 200, we are SB (-4340, showdown loss).**
| street | pot | to_call | range | equity | realized | required | action |
|---|---|---|---|---|---|---|---|
| pre | 300 | 100 | 1.00 | .506 | .380 | .250 | raise 500 (equity >= 0.50 open rule) |
| flop | 1973 | 973 | .60 | .564 | .462 | .330 | call (opp bet 973 into 1000) |
| turn | 5813 | 2867 | .13 | .367 | .331 | .330 | call (opp bet 2867 into 2946) |
| river | 8680 | 0 | .18 | .253 | .253 | 0 | check, opp checks, showdown lost |
Follows from its numbers: yes, all four. The turn call clears the price by 0.001 (.331 vs .330) while the Monte Carlo standard error at 2000 sims is about 0.011 (sqrt(.37*.63/2000)), so the engine acted on noise. Costly assumptions: the range jumps from 0.60 (flop, set by the per-match raise floor) to 0.13 (second aggression, hand-fitted step) with no basis in this opponent's data, and the engine does not price what it commits next (7425 behind, pot 8680).

**Hand 65, KhTh, bb 300, we are SB (-4036, showdown loss).**
| street | pot | to_call | range | equity | realized | required | action |
|---|---|---|---|---|---|---|---|
| pre | 450 | 150 | 1.00 | .618 | .464 | .250 | raise 750, opp calls |
| flop | 1500 | 0 | 1.00 | .589 | .589 | 0 | check (below 0.62 value bar), opp checks |
| turn | 1500 | 0 | 1.00 | .621 | .621 | 0 | bet 990 (just above 0.62), opp calls |
| river | 3480 | 0 | 1.00 | .793 | .793 | 0 | bet 2296, opp calls, we lose |
Follows from its numbers: yes. The costly assumption: range stayed 1.00 on every street because the opponent never raised; the engine narrows only on aggression, never on calls. After the opponent called a 990 bet and then a 2296 river bet, .793 against all hands is a number against a range it no longer faced. The turn bet was 0.001 over the bar.

**Hand 90, AdQd, bb 400, we are BB (-3932, match-ending showdown).** Opp raised to 800 (2 bb). pot 1200, to_call 400, our stack 3532 (8.8 bb), range 0.60, equity .654, realized .491, required .25: action raise all-in 3932. Follows from the rule: stack <= 10 bb and raw equity >= 0.55 shoots. Assumption: 0.60 is the opponent's opening range; its calling range against a shove is unknown (vs_shove n=2) and must be tighter, so .654 is optimistic. Even so a 65% shove losing is ordinary variance; this hand is not evidence of a leak.

**Hand 71, 2c5c, bb 300, we are SB (-2050, showdown loss).** Pre: limp (call 150, equity .377 vs required .25). Flop: opp bets 584 into 600, range .59, equity .439, realized .360 vs .330: call. Turn check. River: pot 1768, bet 1166 with equity 0.000, range .59: a bluff, called. Follows from its numbers: yes (bluff branch: equity < 0.30). Two flags: the flop call clears by 0.03 against a 97%-pot bet; and an equity of exactly 0.000 against a 59% range on the river is suspicious (possible only if the board is such that every combo in the range beats or ties us, which cannot be checked without the board). Check this number before relying on it.

**Hand 89, QdTd, bb 400, we are SB (-1600, fold flop).** Pre: raise 1000 (equity .603). Opp 3-bets to 1600: range 0.60, equity .529, realized .397 vs required .188: call. Flop: opp bets 3115 into 3200, range .13, equity .252, realized .206 vs .330: fold. Follows: yes. Assumption: a 3-bet was credited the same 0.60 as an open (the floor for one raise), while this opponent 3-bets 1 of 22 times (Stats vs_open raise 1/22); a 3-bet from them is far stronger than 0.60. Here the error was cheap (call 600 more, then fold).

Pattern across all five: every decision is consistent with the engine's own numbers; the cost sits in (a) how the range is built (passive calls never narrow; one raise is 0.60 by floor, two is 0.13 by fixed step; neither reflects this opponent) and (b) decisions taken inside Monte Carlo noise (0.001 on hand 59, 0.001 on hand 65).

Other facts: in the 193 decisions of match 1, range was exactly 1.00 in 120 and 0.56-0.65 in 52 (floor-driven; floor = hits/(hands+3), about 0.6 here). Of match 1's 33 calls, 13 cleared the price by less than 0.03 (match 2: 9 of 27). By ending (bb-sum), match 1: opp folds +35.8, showdowns -14.1 (8 won, 10 lost, 1 tie), our preflop folds -30.5 (31 hands), our postflop folds -26.3 (12 hands). Match 2: opp folds +66.0 (73 hands), showdowns -12.9 (4 won, 7 lost, 2 tie), our folds -9.0.

## 3. Match 1 preflop folds against raises (30 of 37)

Method: for each of the 30 folds I re-ran the engine (pokercpp_engine.decide, 20000 sims, same cards, pot, to_call, stack) with the range forced to (a) 0.58, the opponent's observed first-in raise rate (26/45) and (b) 1.00, and compared raw equity and realized (preflop discount 0.75) with the price. All 30 were facing an opponent open (none a 3-bet). 28 of 30 faced the 6.2 bb open (to_call 5.2 bb, required .42); 2 faced a 2 bb open (hands 39, 63).

| range assumed | folds with raw equity > required | folds with realized > required (engine's rule) | raw > required + 0.03 |
|---|---|---|---|
| 0.58 | 14 of 30 | 3 of 30 (hands 16 KdJc, 39 2s8h, 63 2d6h) | 9 |
| 1.00 | 19 of 30 | 4 of 30 (adds 72 Jh2d) | 17 |

- The engine's actual credited range on those folds was 0.32 to 0.63; the first ten (hands 2-18) used 0.32 to 0.50 while the raise floor was still warming up, i.e. narrower than the 58% the opponent showed.
- Answer: by the engine's own call rule, 3 of 30 folds were wrong against the real opening frequency (4 against any hand). The larger count (14, up to 19) depends entirely on the 0.75 preflop realization discount: ignore it and about half the folds look profitable, keep it and almost none do. Whether 0.75 is right for out-of-position hands facing a 6.2 bb raise is not testable from these logs.
- Cost of the folds themselves: 31 preflop folds = -30.5 bb-sum, almost all of it the blind we posted.

## 4. Small-blind limps

| | Match 1 | Match 2 |
|---|---|---|
| SB first actions | 45: raise 23, call 21, fold 1 | 48: raise 27, call 21 |
| after our limp: opp checks | 11 hands, +3967 chips (+9.1 bb-sum) | 19 hands, +395 chips (+2.3 bb-sum) |
| after our limp: opp raises | 10 hands (hands 7,13,17,23,25,39,61,63,85,87), -2000 chips (-8.0 bb-sum) | 2 hands (5, 85), -182 chips (+1.2 bb-sum) |
| all limps | +1.2 bb-sum (+0.05 per hand) | +3.5 bb-sum (+0.16 per hand) |
| our raise-opens (for comparison) | 23: opp call 16 (-8.8), fold 6 (+6.0), 3-bet 1 (-4.0); -6.8 total (-0.30 per hand) | 27: opp fold 24 (+24.0), call 2 (-8.3), 3-bet 1 (+2.8); +18.5 total (+0.68 per hand) |

- Match 1's opponent punished limps by raising 10 of 21 (48%): we folded 8 of those 10 and called 2 (hands 25, 61), costing about 0.8 bb each. Match 2's opponent raised 2 of 21 (10%) and let us see a free flop.
- Limps were roughly break-even in both matches; the limp set is the hands below 0.50 equity vs random, so limp and open results are not like-for-like (selection), and n is 21 each.

## 5. Match 2: how it was won

- 73 of 95 hands (77%) ended with the opponent folding: 63 preflop (+43.5 bb-sum), 5 flop (+11.8), 2 turn (+2.0), 3 river (+8.7). 13 hands reached showdown (14%) and lost 12.9 bb-sum (4 won, 7 lost, 2 chopped). We folded 9 hands (-9.0).
- The opponent was SB in 47 of 95 hands and folded 39 of them without acting further (83%), and folded 24 of 27 to our 2.5 bb opens (89%).
- Stack path: 10970 at hand 20, 12262 at 40, 13437 at 60, 16891 at 80, peak 19241 at hand 91, no large swing; closing hand 95 was an all-in we called for 118 more and won, from 18882 already.
- **Fragile points:** (a) all the profit is one behaviour, folding to opens. Match 1's opponent called 16 of 23 opens and our opens lost 6.8 bb-sum there, so the same strategy flips sign against a caller. (b) Showdowns were net negative; the engine did not win any "value" in the sense of beating hands, it picked up blinds. (c) A single big all-in either way would have moved the result: 3 wins/loss events of the size seen in match 1 (3900-4300 chips) equal a third of the 10000 stack.

## 6. Bench agreement

- Bench (v3 build, 2000 hands, 50/100, results/2026-11-24-bench-results.md): vs nit +60.7 [+47.7, +73.6] bb/100 at 100 bb, +54.4 at 15 bb; vs reference +39.3 / +46.5; vs aggro 15 bb +24.1 [-6.1, +54.2] inconclusive (10,000 hands +6.9 [-6.7, +20.6]); vs station +252.8; vs loosepassive +259.3 at 100 bb.
- Match 2 (nit-like): positive and large (+44.1 bb-sum over 95 hands, about +46 per 100) is in the direction and size the bench gives for nit. Not a confirmation: the standard deviation of one 95-hand match is several times that mean.
- Match 1 (unmatched opponent, loses -35.1 bb-sum): the bench has no opponent that opens 58% to 6 bb, calls 73% of opens and folds 52% postflop. It is not evidence against the bench for station or loosepassive, whose "calls everything" results (+250) came from opponents that never fold postflop.
- Bench cannot reproduce: (1) postflop fit-or-fold plus loose preflop calling in one opponent; (2) the live blind schedule (+50% steps every 20 hands from 100 bb; bench match mode assumes doubling every 25 hands) and the resulting depth path 100 bb to about 10 bb by hand 80; (3) opponents that adapt to what we do (bench opponents are stateless scripts); (4) the 6.2 bb first-in size; (5) the min_raise > max_raise states seen in match 1 (hands 66, 72, 82, 89), which the v4.0.1 fix addresses.

## 7. HYPOTHESES (ranked by expected impact; none established)

**H1. Preflop folds to a wide 6.2 bb opener are too tight because of the 0.75 realization discount.** Evidence: 28 of 30 match 1 preflop folds faced the 6.2 bb open; 14 of 30 had raw equity above the price vs a 0.58 range (19 vs any hand) but only 3 (4) clear it after discounting; preflop folds cost -30.5 bb-sum. Test: `decideFull` already takes `realizationScale` (comment: exists so bench.py can A/B it). Opponent aggro (6 bb sizing, widest-range raiser; reference as control, since it opens only 3%); depths 15, 25 and 100 bb; 2000 swapped pairs per cell, two seed sets (seed0 700001 and 710001); paired comparison: the same build with preflop realization 0.75 vs 0.85 and 0.95 (scale 1.13, 1.27), difference in bb/100 with a paired interval; accept only if the interval is above 0 on both seed sets and the reference control is not below 0.

**H2. The engine does not narrow its range when the opponent only calls, so thin value bets into callers lose.** Evidence: hand 65 (-4036): range 1.00 on all four streets, river bet 2296 after opp called a turn bet, equity .793 against a range the opponent no longer held; hand 71 (-2050, bluff called); match 1 opponent called 4 of 7 river bets; 120 of 193 match 1 decisions at range 1.00. Test (needs a new engine option: after the opponent calls a bet on a street, narrow the range by a fixed factor, for example 0.6 per call): opponents reference (calls with pair or better, so it holds a real narrowed range) and loosepassive; station as control (calls everything, narrowing should hurt or be neutral); 100 and 15 bb; 2000 pairs, two seed sets; paired comparison new build vs v4.0.1 on the same seeds. Refuted if reference shows no gain.

**H3. Calls decided inside Monte Carlo noise are a loss source.** Evidence: hand 59 turn call 2867 at margin 0.001 (standard error 0.011) = the largest single loss; 13 of 33 calls in match 1 and 9 of 27 in match 2 within 0.03 of the price. Test: engine hero, sims 2000 vs 10000 (paired, same seeds) and a variant that folds calls facing a bet over 50% of pot on turn and river unless margin >= 0.03; opponents aggro, september and reference; depths 15 and 100 bb; 2000 pairs, two seed sets. Refuted if sims 10000 changes nothing and the margin rule loses vs aggro.

**H4. The fixed range steps (0.60 to 0.13 on the second aggression, 0.60 on a 3-bet) misread this kind of opponent.** Evidence: hand 59 flop .60 then turn .13; hand 89 a 3-bet credited 0.60 while the opponent 3-bets 1 of 22; hands 89 and 60 folded the flop to a bet at range .13 after paying preflop (match 1 postflop folds -26.3 bb-sum, 12 hands); match 1 opponent bets 44% when checked to. Test: `rangeFloor` argument exists; compare floor 0.30 applied to any aggression against current, versus aggro and maniac (wide bettors, where narrower assumed ranges mean over-folding) and reference (control, bets only strong hands: a wider assumed range should lose); 15 and 100 bb; paired; plus a sanity run at 25 bb. Refuted if aggro/maniac show no gain or reference loses.

**H5. Against an opponent that folds first-in above 80%, limping the SB gives up steals.** Evidence: match 2, limps +0.16 per hand against opens +0.68 per hand; the opponent folded 24 of 27 opens, checked 19 of 21 limps, raised only 2. Weak evidence (n=21 and 27, selection). Test (needs OPEN_EQ exposed): nit (and a nit variant with 3-bet shoves), reference, then aggro as downside control; 15 and 100 bb; compare OPEN_EQ 0.50 vs 0.0 (always open); paired; keep only if nit and reference gain and aggro is not significantly worse. Real-world gate: an opponent model would have to detect the folder first (first-in fold rate over the first 20 hands), which the live opponent counts (Stats) could provide.

## What two matches cannot tell us

- Two different opponents, one result each; a 90-hand and a 95-hand match with per-hand standard deviation in the several-bb range. Nothing here is statistically separable from variance. Match 1's result is carried by three hands (59, 65, 90 = -12308 chips against a total of -10000; the other 87 hands net +2308).
- We never saw an opponent hole card, so every statement about the opponent's range is inferred from actions; we also lack boards after the first 50 decisions.
- Opponent behaviour may depend on our play and may change within a match; the Stats counts are per-match and small (cbet n=5 and 2, vs_shove n=2).
- The bench cannot say how a real field plays, as the v4 release note already states; the bench tests in section 7 only check whether a change is harmless or helpful against scripted opponents.
