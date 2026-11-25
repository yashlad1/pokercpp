# Slumbot baseline (25 Nov 2026)

**Question:** how does the bot do against Slumbot, a near-GTO opponent, and where does it leak? First use of the public Slumbot API (issue #34), through the new `tools/slumbot.py`.

**What and how**
- **Sessions:** anonymous, on the token the API returns. No login.
- **Game:** blinds 50/100, 200 bb stacks reset every hand, positions as the API deals them (alternating).
- **Pacing:** one request at a time, 0.2 s pause between hands, at most two retries per request. Latency was about 0.15 s per request (p95 about 0.2 s). The 500-hand run took 439 s, the 200-hand run 170 s.
- **Hero:** driven through the bench View, so the same decision code plays as in the bench: `PokerCpp` (engine) and `Bot` (`chipzen/bot.py`), 2000 sims.
- **Unpaired:** the deals are random and cannot be replayed, so there is no seat-swap pairing. The interval comes from the per-hand standard deviation, which is much wider than the paired intervals in the other result notes.

**Checks:** a 20-hand smoke, then both runs: every action accepted (0 rejected), and each hand's chips recomputed from the action string and the revealed cards matched Slumbot's reported winnings (0 mismatches over about 2,900 requests).

| Run | Hands | Chips | bb/100 (95% interval) | VPIP | Preflop raise | Showdown wins |
|---|---|---|---|---|---|---|
| engine, 2000 sims | 500 | -72,276 | -144.6 [-306.2, +17.1] | 91.2% (456/500) | 22.0% (110/500) | 47 of 125 (37.6%) |
| bot, 2000 sims | 200 | -79,338 | -396.7 [-761.3, -32.1] | 88.5% (177/200) | 25.0% (50/200) | 15 of 56 (26.8%) |

**Breakdown from the hand logs** (the smoke run is a third, tiny log of 20 hands: +6,377 chips, 1 showdown, not used below)

By seat, chips per hand:

| Run | Small blind | Big blind |
|---|---|---|
| engine (500) | -137.9 (250 hands) | -151.2 (250 hands) |
| bot (200) | -437.4 (100 hands) | -356.0 (100 hands) |

By how the hand ended, hands (share) and chips (per hand):

| Run | We fold | Slumbot folds | Showdown |
|---|---|---|---|
| engine | 211 (42%), -57,304 (-271.6) | 164 (33%), +90,045 (+549.1) | 125 (25%), -105,017 (-840.1) |
| bot | 74 (37%), -24,110 (-325.8) | 70 (35%), +22,039 (+314.8) | 56 (28%), -77,267 (-1,379.8) |

The whole loss sits in showdowns: the bot wins small pots when Slumbot folds and loses big ones when it gets to showdown.

Preflop:
- **First action a fold:** engine 23 of 500 (4.6%), bot 10 of 200 (5.0%).
- **Big blind facing Slumbot's open:** engine called 212, folded 15, re-raised 2 (of 229, 93% called). Bot called 77, folded 8, re-raised 2 (of 87, 89% called).
- **Small blind facing a 3-bet after our raise:** engine called 28, folded 1 (of 29). Bot called 12 (of 12). It never folded to a 3-bet and never 4-bet.
- **Small blind that limped, then faced a raise:** engine folded 62, called 8 (of 70). Bot folded 15, called 2 (of 17). Limping and then folding gives up the blind often.

**Caveats**
- **Depth:** Slumbot plays 200 bb deep. The Chipzen games start at 100 bb, and the bench numbers elsewhere are at 15 and 100 bb, so these are not comparable.
- **What it measures:** Slumbot is near-GTO and every hand resets, so this shows leaks, not adaptation to an opponent.
- **Sample size:** 500 and 200 hands are thin. The engine interval includes zero, the bot interval barely excludes it, and the two intervals overlap. Do not read the gap between engine and bot as real.
- **Terms of use:** none were found on the API or in Slumbot's sample client. The repo owner approved this use. Pacing was kept polite.
- **Known small inaccuracy:** in the Bot agent's history, an all-in call is labelled `call`, not `all_in`. It does not affect the result of any hand here.

## Rerun (25 Nov 2026, after merging main at 70174d7)

**Local only, never in CI; calls an outside service; results are unpaired.** `tools/slumbot.py` is not in the CI workflow.

Same settings as above (2000 sims, 200 bb deep, 0.2 s between hands, sequential, engine first). A 20-hand smoke first: 0 rejected, 0 mismatches. Latency about 0.11 s per request (p95 about 0.12 s).

| Run | Hands | Chips | bb/100 (95% interval) | VPIP | Preflop raise | Showdown wins | Rejected / mismatches | Wall time |
|---|---|---|---|---|---|---|---|---|
| engine, first run | 500 | -72,276 | -144.6 [-306.2, +17.1] | 91.2% (456/500) | 22.0% (110/500) | 47 of 125 (37.6%) | 0 / 0 | 439 s |
| engine, rerun | 500 | -104,764 | -209.5 [-431.1, +12.0] | 87.4% (437/500) | 22.2% (111/500) | 42 of 112 (37.5%) | 0 / 0 | 329 s |
| bot, first run | 200 | -79,338 | -396.7 [-761.3, -32.1] | 88.5% (177/200) | 25.0% (50/200) | 15 of 56 (26.8%) | 0 / 0 | 170 s |
| bot, rerun | 200 | -19,096 | -95.5 [-458.1, +267.1] | 92.5% (185/200) | 23.0% (46/200) | 18 of 39 (46.2%) | 0 / 0 | 137 s |

- **Reading:** the engine rerun overlaps the first run. The bot rerun moved a lot (-396.7 to -95.5), and both bot intervals overlap, so that is sample noise on 200 random hands, not a change in the bot. Both engine reruns still lose; neither bot interval can be told apart from the engine's.
- **Privacy:** requests carry no identifying data (urllib's default User-Agent, the anonymous session token in the body only). The token is never written to the hand log or to stdout.

Eval log rows (Runs sheet, unpaired: only the A columns are filled): R296 and R297 are the two first runs carried over from the earlier rows R190 and R191 (renumbered after main's R295); R298 is the engine rerun and R299 the bot rerun.
