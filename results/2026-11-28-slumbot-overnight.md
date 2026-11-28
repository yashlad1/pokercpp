# Overnight Slumbot run for v4.1.0: 35 sessions of 1,000 hands (27-28 Nov 2026)

**Question:** over a long automatic run, does the live bot (v4.1.0: preflop realization 0.85, opponent stats) win or lose against Slumbot, session by session, and why does it lose the hands it loses? Same tool and format as the [27 Nov single session](2026-11-27-slumbot-v410.md).

**What and how**
- **Build:** main at 0260941, engine built with `tools/build_engine.sh`; `build_info()` reported `git_sha 0260941, preflop_realization 0.85, call_narrow 1.0`.
- **Hero:** `chipzen/bot.py` through the bench View (`--hero bot`), 5000 sims (the live setting).
- **Sessions:** 35 anonymous sessions of 1,000 hands, seeds 2001 to 2035 (seed 2000 plus the session number). Blinds 50/100, 200 bb stacks reset every hand, seats as the API deals them.
- **Pacing:** one request at a time, 0.2 s between hands, at most two retries, 60 s between sessions. A session took 654 to 716 s (23,828 s in all); mean latency per request 0.097 to 0.109 s, 152,549 requests in total.
- **Times (ET):** the run began 22:11 on 27 Nov and the last session ended 05:22 on 28 Nov. It stopped on its own because fewer than 15 min were left before the 05:30 deadline.
- **Checks:** every session reported 0 rejected actions and 0 reconcile mismatches. The logs hold no session token (the fields are action, board, bot_hole, client_pos, decisions, expected, hole, showdown, winnings).
- **Unpaired:** the deals are random, so every interval comes from per-hand or per-session spread, not from a paired design. As in the 27 Nov run, `expected` equals the actual result, so the report's "expected-based" figure is the raw figure.
- **Analysis:** `tools/slumbot_report.py` per log and over all 35; `tools/slumbot_luck.py` (all-in adjusted, #192) and its per-street version; `tools/slumbot_why.py` (cause of each big loss); `tools/range_lab.py`. Versions are in the caveats.
- **Logs:** `results/slumbot-logs/2026-11-27-night/session-01.jsonl.gz` to `session-35.jsonl.gz`, 2.1 MB gzipped (24 MB plain).

## Per session

bb/100 here is chips per hand (a big blind is 100 chips). The interval is the per-hand one from `slumbot_report.py` (mean ± 1.96 × sample SD / √1000). "Big losses" are hands that lost 20 bb or more; the last column is the largest cause by chips among them, from `slumbot_why.py`: hands and chips.

| # | Seed | Chips | bb/100 (95% interval) | Result | Secs | Big losses | Largest cause (hands, chips) |
|---|---|---|---|---|---|---|---|
| 1 | 2001 | 39,855 | +39.9 [-72.1, +151.8] | win | 680 | 27 | overconfident vs his hand (20, -109,948) |
| 2 | 2002 | -85,404 | -85.4 [-236.4, +65.6] | loss | 691 | 36 | overconfident vs his hand (33, -272,682) |
| 3 | 2003 | -119,625 | -119.6 [-247.6, +8.4] | loss | 684 | 37 | overconfident vs his hand (32, -231,206) |
| 4 | 2004 | -69,466 | -69.5 [-188.3, +49.4] | loss | 693 | 33 | overconfident vs his hand (29, -188,979) |
| 5 | 2005 | -35,556 | -35.6 [-165.3, +94.2] | loss | 704 | 28 | overconfident vs his hand (28, -194,626) |
| 6 | 2006 | -111,888 | -111.9 [-249.4, +25.6] | loss | 695 | 35 | overconfident vs his hand (32, -245,484) |
| 7 | 2007 | -97,070 | -97.1 [-210.9, +16.8] | loss | 716 | 34 | overconfident vs his hand (33, -195,147) |
| 8 | 2008 | 20,030 | +20.0 [-101.7, +141.7] | win | 711 | 32 | overconfident vs his hand (26, -143,313) |
| 9 | 2009 | 113,819 | +113.8 [-30.0, +257.7] | win | 703 | 28 | overconfident vs his hand (26, -158,198) |
| 10 | 2010 | -19,832 | -19.8 [-105.6, +66.0] | loss | 692 | 24 | overconfident vs his hand (19, -109,315) |
| 11 | 2011 | -138,669 | -138.7 [-277.1, -0.2] | loss | 679 | 42 | overconfident vs his hand (38, -276,494) |
| 12 | 2012 | -118,966 | -119.0 [-266.5, +28.6] | loss | 699 | 35 | overconfident vs his hand (32, -266,487) |
| 13 | 2013 | -114,346 | -114.3 [-260.3, +31.6] | loss | 715 | 31 | overconfident vs his hand (29, -272,611) |
| 14 | 2014 | -70,165 | -70.2 [-232.7, +92.4] | loss | 698 | 35 | overconfident vs his hand (32, -286,387) |
| 15 | 2015 | 22,678 | +22.7 [-92.4, +137.8] | win | 694 | 30 | overconfident vs his hand (22, -131,763) |
| 16 | 2016 | -53,326 | -53.3 [-195.4, +88.7] | loss | 685 | 40 | overconfident vs his hand (36, -232,561) |
| 17 | 2017 | -71,614 | -71.6 [-210.6, +67.4] | loss | 710 | 36 | overconfident vs his hand (33, -243,488) |
| 18 | 2018 | -4,027 | -4.0 [-143.1, +135.0] | loss | 672 | 28 | overconfident vs his hand (24, -174,632) |
| 19 | 2019 | -66,280 | -66.3 [-222.0, +89.5] | loss | 675 | 34 | overconfident vs his hand (29, -254,609) |
| 20 | 2020 | -111,090 | -111.1 [-269.8, +47.6] | loss | 674 | 35 | overconfident vs his hand (31, -281,112) |
| 21 | 2021 | -82,310 | -82.3 [-200.7, +36.1] | loss | 671 | 26 | overconfident vs his hand (24, -161,676) |
| 22 | 2022 | -46,458 | -46.5 [-165.3, +72.4] | loss | 679 | 36 | overconfident vs his hand (27, -177,896) |
| 23 | 2023 | -23,858 | -23.9 [-174.6, +126.9] | loss | 672 | 39 | overconfident vs his hand (35, -241,218) |
| 24 | 2024 | -37,072 | -37.1 [-166.7, +92.6] | loss | 657 | 33 | overconfident vs his hand (28, -170,345) |
| 25 | 2025 | 76,340 | +76.3 [-66.9, +219.6] | win | 665 | 25 | overconfident vs his hand (24, -193,261) |
| 26 | 2026 | -23,082 | -23.1 [-124.5, +78.4] | loss | 664 | 24 | overconfident vs his hand (22, -148,508) |
| 27 | 2027 | -9,516 | -9.5 [-140.8, +121.8] | loss | 654 | 34 | overconfident vs his hand (31, -187,524) |
| 28 | 2028 | -50,709 | -50.7 [-196.6, +95.2] | loss | 661 | 37 | overconfident vs his hand (35, -257,250) |
| 29 | 2029 | -99,917 | -99.9 [-253.4, +53.5] | loss | 656 | 39 | overconfident vs his hand (37, -289,845) |
| 30 | 2030 | -146,232 | -146.2 [-295.3, +2.9] | loss | 660 | 36 | overconfident vs his hand (28, -254,797) |
| 31 | 2031 | -60,075 | -60.1 [-167.2, +47.0] | loss | 661 | 39 | overconfident vs his hand (37, -159,158) |
| 32 | 2032 | -153,218 | -153.2 [-267.8, -38.7] | loss | 659 | 29 | overconfident vs his hand (26, -214,980) |
| 33 | 2033 | -8,306 | -8.3 [-133.0, +116.4] | loss | 666 | 32 | overconfident vs his hand (26, -188,928) |
| 34 | 2034 | -95,619 | -95.6 [-236.6, +45.4] | loss | 673 | 34 | overconfident vs his hand (30, -221,580) |
| 35 | 2035 | -15,672 | -15.7 [-152.1, +120.7] | loss | 660 | 29 | overconfident vs his hand (24, -191,337) |

Result: **5 sessions won, 30 lost**. Best session 9 at +113.8, worst session 32 at -153.2. Only two sessions have an interval that excludes zero (11 and 32, both losses); the five wins are all inside their own noise.

## Spread check

Is the session-to-session spread bigger than the per-hand noise predicts? The per-hand SD over all 35,000 hands is 2,163 chips, so one session of 1,000 hands should have an SD of 2,163 / √1,000 = 68.4 bb/100.

| | Value |
|---|---|
| SD of the 35 per-session bb/100 | 61.8 |
| Predicted SD from the per-hand SD | 68.4 |
| Ratio, observed / predicted | 0.90 |
| Sessions within ±1 predicted SD of the pooled mean | 27 of 35 (77%); 23.9 expected from a normal |
| Sessions within ±2 predicted SDs | 34 of 35 (97%); 33.4 expected |

The spread is what independent 1,000-hand samples of one fixed result would give, a little tighter if anything. Nothing here points to a drifting opponent or a bot whose strength changed between sessions; 5 wins out of 35 is what a true mean near -53 produces.

## Pooled result

| Basis | Hands | Chips | bb/100 (95% interval) |
|---|---|---|---|
| Per-hand SD (`slumbot_report.py`) | 35,000 | -1,866,646 | -53.3 [-76.0, -30.7] |
| Session level: mean of 35, SE 61.8 / √35 = 10.5, t interval | 35,000 | | -53.3 [-74.6, -32.1] |

The two intervals agree. The pooled result is a loss; the interval excludes zero. The 27 Nov single session (-58.9 [-214.2, +96.5]) sits inside it.

Other pooled figures from the report: VPIP 95.0% (33,243 of 35,000), preflop raise 25.7% (8,992), showdown wins 3,778 of 9,868 (38.3%, a split counts as not won). By seat, chips per hand: small blind -34.9 (17,500 hands, -611,146), big blind -71.7 (17,500 hands, -1,255,500). By ending:

| We fold | Slumbot folds | Showdown |
|---|---|---|
| 11,641 (33%), -3,794,731 (-326.0) | 13,491 (39%), +6,210,735 (+460.4) | 9,868 (28%), -4,282,650 (-434.0) |

Preflop: big blind facing Slumbot's open called 15,457, folded 4, re-raised 286 (of 15,747); small blind facing a 3-bet after our raise called 2,075, re-raised 65 (of 2,140); small blind that limped then faced a raise called 1,494 and folded 2,343 (of 3,837).

## Luck-adjusted figures

`slumbot_luck.py` replaces the result of a hand where both players were all-in before the river with our equity at that moment (84 of 35,000 hands). The per-street version also replaces the money won on each deal with its equity change (29,547 hands that saw a deal and showed Slumbot's cards).

| Basis | Chips | bb/100 (95% interval) | SD per hand | SD ratio vs raw |
|---|---|---|---|---|
| Raw | -1,866,646 | -53.3 [-76.0, -30.7] | 2,163 | 1 |
| All-in adjusted (merged tool, 20,000-board preflop equities) | -2,029,946 | -58.0 [-79.7, -36.3] | 2,070 | 0.957 |
| All-in adjusted (per-street tool, 1,000-board preflop equities) | -2,029,801 | -58.0 [-79.7, -36.3] | 2,070 | 0.957 |
| Street adjusted (per-street tool, 1,000-board preflop equities) | -2,016,931 | -57.6 [-76.6, -38.7] | 1,806 | 0.835 |

Luck did not hide a better bot: the adjusted figures are 4 to 5 bb/100 worse than raw, not better, and all three bases agree on a loss near 55 to 60. Street adjustment cuts the SD by about 17%, so its interval is narrower. The 20,000 and 1,000-board all-in figures differ by 145 chips in 2 million, which is the Monte Carlo noise at the smaller board count.

## Why the bot lost

Three views, from the hands themselves. All use Slumbot's revealed cards, so they are hindsight about this one set of deals.

**1. Where the chips went.** The bot wins chips when Slumbot folds (+6.21 M) and loses them at showdown (-4.28 M) and by folding itself (-3.79 M). It plays almost every hand (VPIP 95%) and calls 98% of Slumbot's opens from the big blind, so showdown pots are large and many. The showdown loss is the biggest single bucket and is what the next two views explain.

**2. Cause of the big losses (`slumbot_why.py`).** 1,152 hands lost 20 bb or more, -7,849,798 chips (four times the net loss of -1.87 M; the rest of the play wins back about 6 M). Each is judged at the decision that put the last chips in, with the true equity against Slumbot's actual hand.

| Cause | Hands (share) | Chips (share of big-loss chips) |
|---|---|---|
| Overconfident vs his real hand (logged equity at least 0.25 above true equity) | 1,018 (88.4%) | -7,327,345 (93.3%) |
| Bluff called | 67 (5.8%) | -216,473 (2.8%) |
| Right decision, unlucky run-out | 34 (3.0%) | -212,846 (2.7%) |
| Folded the best hand | 22 (1.9%) | -62,400 (0.8%) |
| Marginal decision lost | 11 (1.0%) | -30,734 (0.4%) |

In all 35 sessions "overconfident" is the largest cause. Inside it: 883 of the 1,018 hands are on the river, 113 on the turn, 22 on the flop; 583 are calls and 435 are bets or raises that were then called or re-raised to all-in; the seat split is even (517 big blind, 501 small blind). River calls alone are -3.46 M, turn calls -0.70 M. Mean logged equity on these hands is 0.64; on the river the true equity against his cards is 0 or 1, and in these hands it was 0, so this label is partly the hindsight of picking lost hands. The next view does not select on losing.

The five worst hands (all -20,000; the first five by session and hand among 150 that lost a full stack):
- session 01 hand 662, -20,000 chips, SB: overconfident vs his real hand: As/Js vs his Jd/Th on 4 board cards: b19750 with true equity 0.03, needed 0.38 (logged 0.75, range 0.370253164556962).
- session 02 hand 210, -20,000 chips, SB: overconfident vs his real hand: 2d/2c vs his Qd/Qc on 5 board cards: c with true equity 0.00, needed 0.33 (logged 0.86, range 0.055999999999999994).
- session 02 hand 470, -20,000 chips, SB: overconfident vs his real hand: Kh/3h vs his 6s/6c on 5 board cards: c with true equity 0.00, needed 0.31 (logged 0.86, range 0.055999999999999994).
- session 02 hand 626, -20,000 chips, SB: overconfident vs his real hand: 7c/6d vs his Js/4d on 5 board cards: c with true equity 0.00, needed 0.31 (logged 0.76, range 0.10517529215358931).
- session 02 hand 690, -20,000 chips, SB: overconfident vs his real hand: 4s/3s vs his 9s/3c on 5 board cards: c with true equity 0.00, needed 0.32 (logged 0.92, range 0.4395770392749245).

**3. Calibration over every showdown (not selected on losing).** Our last logged equity against the share of showdowns won (`results/2026-11-28-slumbot-overnight-scripts/calibration.py`; a split counts half, unlike the report's bucket table).

| Logged equity | Showdowns | Mean logged | Won | Chips |
|---|---|---|---|---|
| below 0.5 | 6,016 | 0.303 | 0.307 | -2,170,901 |
| 0.5-0.6 | 1,458 | 0.548 | 0.537 | -696,167 |
| 0.6-0.7 | 772 | 0.643 | 0.434 | -1,283,465 |
| 0.7-0.8 | 519 | 0.743 | 0.453 | -705,078 |
| 0.8 and up | 1,103 | 0.912 | 0.767 | +572,961 |
| River calls facing a bet | 2,639 | 0.468 | 0.310 | -2,782,214 |

Below 0.6 the estimate matches what happened. From 0.6 up the bot wins 20 to 30 points less often than it thinks, and the river calls it makes against a bet win 31% of the time against a logged 47%, for -2.78 M, more than the whole net loss. The bot's equity is computed against a modelled range for Slumbot; when Slumbot bets or raises late, its real range is stronger than that model. That agrees with the 27 Nov 0.7-0.8 bucket (8 of 20) with 519 hands in the bucket instead of 20. Selection applies (only hands that reached showdown), so read it as a strong direction, with the 0.6-0.8 gap larger than any binomial noise at these counts (772 and 519 hands), and not as an exact leak size.

**In short:** the loss is not luck (the adjusted figures are worse than raw), not drift between sessions (the spread matches the noise), and not a few unlucky stacks. It is consistent with one repeated pattern: late-street calls and raises made on an equity figure that is too high against Slumbot's real range, in both seats, costing most at the river. The "right decision, unlucky run-out" cause is only 2.7% of big-loss chips. This is a description of this sample; it does not show that changing the range model would fix it.

## Range lab (#37)

Per street, how often the hand Slumbot showed falls inside the range the bot used at each of its decisions. Hard is today's top-X% range. Weighted is a board-aware weighted range built from his actions, scored two ways: by the same top mass (mass), and by taking as many top combos as the hard range holds (count-matched, the like-for-like comparison). Log scores are the mean of log(probability × live combos); higher is better, 0 is no information.

| Street | Decisions | Hard range holds his hand | Weighted, count-matched | Weighted, same mass | Log score, weighted | Log score, hard |
|---|---|---|---|---|---|---|
| Preflop | 39,251 | 93.7% | 93.7% | 70.1% | -0.303 | -0.003 |
| Flop | 36,503 | 82.5% | 80.5% | 49.3% | -0.570 | -0.193 |
| Turn | 24,417 | 73.6% | 72.6% | 42.0% | -0.607 | -0.411 |
| River | 17,378 | 67.1% | 70.6% | 36.5% | -0.457 | -0.568 |

Count-matched, the weighted range does not beat the hard one before the river (equal preflop, 2.0 and 1.0 points behind on flop and turn) and is ahead on the river by 3.5 points; the log scores say the same (hard better to the turn, weighted better on the river). The hard range holds his hand only 67% of the time on the river, which is the same late-street gap the calibration shows from the other side.

## Reproduce

```
gunzip -k results/slumbot-logs/2026-11-27-night/session-*.jsonl.gz
PYTHONPATH=chipzen python tools/slumbot_report.py results/slumbot-logs/2026-11-27-night/session-*.jsonl
PYTHONPATH=chipzen python tools/slumbot_luck.py results/slumbot-logs/2026-11-27-night/session-*.jsonl
python tools/slumbot_why.py --out why results/slumbot-logs/2026-11-27-night/session-*.jsonl   # at 9deab9b
PYTHONPATH=chipzen python results/2026-11-28-slumbot-overnight-scripts/luck_p1b_1000.py <tools dir at fec2a10> results/slumbot-logs/2026-11-27-night/session-*.jsonl
python results/2026-11-28-slumbot-overnight-scripts/range_lab_sharded.py <tools dir at 00f1fb4> "results/slumbot-logs/2026-11-27-night/session-*.jsonl" rangelab.json
python results/2026-11-28-slumbot-overnight-scripts/calibration.py results/slumbot-logs/2026-11-27-night/session-*.jsonl
```

The `gunzip -k` comes first; the plain `.jsonl` files stay out of git. The session-level spread check uses the per-session bb/100 from the first table and the per-hand SD of 2,163 chips.

## Caveats

- **Tool versions:** `slumbot_report.py` and `slumbot_luck.py` (all-in adjusted) are on main at c499246 (#192). The per-street luck version is an unmerged PR head, fec2a10. `slumbot_why.py` is an unmerged PR head, 9deab9b (#189). `range_lab.py` is PR #191 at 00f1fb4. Numbers from those three can change if the PRs change.
- **Reduced preflop Monte Carlo (per-street luck):** the tool's default is 20,000 boards for every preflop equity. Over 35,000 hands that is about 29,000 distinct equities and would take about 80 hours here, so the per-street figures were run with 1,000 boards per equity (`luck_p1b_1000.py` sets the tool's constant and leaves the file untouched). The added noise lands only on the flop-deal corrections, whose pot is the small preflop pot, and on the preflop all-in hands; it moved the all-in adjusted total by 145 chips of 2.03 M (see the table). This runtime is part of why issue #194 matters.
- **Range lab run sharded:** `range_lab_sharded.py` splits the hands over processes after computing his pooled action rates once from all 35,000 hands, then recombines the per-street sums, so the totals equal a serial run; the serial run would have taken about two hours.
- **Hindsight:** the cause table and the five worst hands use Slumbot's revealed hand. "Overconfident" on a river call that lost is true by construction; the calibration table is the part not selected on losing, and it only covers showdowns.
- **Slumbot is near-GTO:** a loss of about 53 bb/100 against it says the bot is exploitable by a near-equilibrium player, not that it loses to typical opponents. It plays 200 bb deep and every hand resets to 200 bb, so this shows leaks, not adaptation or bankroll behaviour; Chipzen games start at 100 bb.
- **Interval choice:** the per-hand interval treats the hands as independent draws, which random deals justify; the session-level interval agrees with it.
- **Not in PR checks:** `tools/slumbot.py` calls an outside service, so these sessions are not re-run by CI.
