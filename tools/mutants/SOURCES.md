# B1 catalogue sources (origin/main a2e70b4)

expect lists only deterministic killers; flaky killers are noted, not expected

- M1 / parity: MEASURED. review table (2026-11-25-review-pr91-pr92.md) P0-P4 F
- M1 / sdk: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M1 / v4: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M1 / replay: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M2 / parity: MEASURED. review table (2026-11-25-review-pr91-pr92.md) P0-P3 F (not re-measured on today's parity)
- M2 / villain_raises: PREDICTED. test_villain_raises.py:38-39 all_in must count 1; :55 own all_in seen from seat 0 == 3; :61 mixed == 3
- M3 / parity: MEASURED. A3 (aggro 230 action mismatches, random 75)
- M3 / villain_raises: PREDICTED. test_villain_raises.py:55 == 3 and :61 == 3
- M4 / parity: MEASURED. review table (2026-11-25-review-pr91-pr92.md) P0-P4 F
- M4 / sdk: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M4 / v4: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M4b / opponent: PREDICTED. test_opponent.py:57-58 (five hands, k=1 expects 4/8) and :64, :70
- M5 / sdk: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M5 / v4: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- M6 / v4: MEASURED. review table (2026-11-25-review-pr91-pr92.md) (T10)
- M6 / replay: MEASURED. review table (2026-11-25-review-pr91-pr92.md) (#87 hand 11)
- M6 / wire: PREDICTED. test_wire.py:87-88 bounds (400,300) with raise offered must give exactly 300
- M7 / parity: MEASURED. review table (2026-11-25-review-pr91-pr92.md) P0-P3 F (not re-measured on today's parity)
- M7 / wire: PREDICTED. test_wire.py:82-83 reply 'call' with valid ['all_in'] must stay in valid
- M8 / sdk: MEASURED. review table (2026-11-25-review-pr91-pr92.md) (one check); user: sdk only while bench offers all_in
- M8 / parity: MEASURED in B2 (#115): live-wire parity fails (aggro 3, random 3 pair mismatches)
- D1 / sdk: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- D1 / solver: MEASURED. review table (2026-11-25-review-pr91-pr92.md)
- D2 / preflop_realization: MEASURED on the 0.85 candidate (C2), macOS: tools/mutants/run.py --only D2 kills it. D2 now mutates 0.85 to 0.75; the solver test no longer kills it because its fold pins hold at 0.75 too.
- Solver test seeds: its seeded shuffle order differs between libc++ (macOS) and libstdc++ (Linux CI), so a seeded kill is deterministic per platform. D2's kill was measured on macOS, where run.py runs.
- D3 / decide_properties: MEASURED. A2 (159 checks)
- D4 / decide_properties: MEASURED. A2 (2 checks)
- D5 / decide_properties: MEASURED. A2 (29 checks)
- D6 / decide_properties: MEASURED. A2 (146 checks)
- E1 / eval_exhaustive: MEASURED. A1 (9,197 disagreements)
- E2 / eval_exhaustive: MEASURED. #130 full mutant run killed E2 with eval_exhaustive (SF hands counted as flushes, so the SF and flush totals mismatch)
- E1 / eval_order: MEASURED. #134 (run.py --only E1,E2)
- E2 / eval_order: MEASURED. #134 (run.py --only E1,E2)
- E3 / eval_order: MEASURED. M-1 (#104): the new test fails on E3 (score does not rise with the reference key); eval_exhaustive still passes it
- T1 / match: MEASURED. A4 (h=21)
- T2 / match: MEASURED. A4 (h=1)
- T3 / match: MEASURED. A4 (h=20)
- T4 / match: MEASURED. A4 (h=1 TypeError)
- T4 / wire_default: MEASURED. #141 full mutant run
- B1 / bench_coerced: MEASURED. run.py --only B1 (the counter adds 0, so the coerced-count test fails); no other test kills it
- T5 / match: MEASURED. run.py --only T5 (a match at a 50 first big blind starts at 5,000 chips, the mutant gives 10,000; #111)
- CN1 / call_narrow: MEASURED. this run (#84, run.py --only CN1..CN5)
- CN2 / call_narrow: MEASURED. this run (#84, run.py --only CN1..CN5)
- CN3 / call_narrow: MEASURED. this run (#84, run.py --only CN1..CN5)
- CN4 / call_narrow: MEASURED. this run (#84, run.py --only CN1..CN5)
- I1 / import_logs: MEASURED. full run.py (the running-process check is off, so the refuse-while-running and whole-call-refusal tests fail); no other test kills it
- I2 / import_logs: MEASURED. full run.py (the stamp is the first 19 characters again, so the warning-first-line and absolute-path tests fail); no other test kills it
- ST1 / opponent_stats: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: call_narrow, opponent_stats, parity, sdk, v4, villain_raises). every hand-built case reads the wrong seat as the opponent; also villain_raises, since bot.py counts through parse_actions
- ST1 / villain_raises: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: call_narrow, opponent_stats, parity, sdk, v4, villain_raises). test_villain_raises.py counts the opponent's raises from seat 0 and seat 1
- ST2 / opponent_stats: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: opponent_stats). the bench round-end-path tests and the oracle lose every fold-after-our-last-bet (vs_bet)
- ST3 / opponent_stats: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: opponent_stats). the shove cases of first_in, vs_open and the live-log oracle expect shove, not raise
- ST4 / opponent_stats: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: call_narrow, opponent_stats, parity, villain_raises). a blind read as a raise makes the opponent's blind the first action
- ST4 / villain_raises: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: call_narrow, opponent_stats, parity, villain_raises). the opponent's blind post would count as a raise in test_villain_raises.py
- ST5 / opponent_stats: MEASURED (mutant run on 88d10f5, 27 Nov, full kill set: opponent_stats). test_live_seat_path_from_is_self_without_my_seat_or_decide: with the is_self test inverted the live seat is the other one, so the counts flip

## Out of scope
- Metal bias mutants: +0.03 equity and +0.002 equity in the Metal path (A5, PR #96). They need Metal builds.

## Notes
- parity for M2/M7 is from the review table's P0/P3 columns, not re-measured on today's tools/test_parity.py.
- E2 is the one-edit form (SF code 8 lowered to 5), because the runner takes a single find/replace.
- BI1 / logging: MEASURED (as predicted). test_logging b3 and s1 compare the full line with engine=; b4 omits it
- BI1 / v4: MEASURED (as predicted). test_v4 T7 builds the full line from bot.VERSION and build_info
- BI2 / logging: MEASURED (as predicted). only b2 compares build_info git_sha with git HEAD; T7, s1 and b3 take the expectation from build_info, so v4 should not kill it
- PM1 / play_match: MEASURED. full run.py (each SDK run plays all the matches again, so the one-match-per-run and stop-on-failure tests fail); no other test kills it
- D2 / logging: MEASURED on #179 (b1 asserts build_info preflop_realization == 0.85)
- SR1 / slumbot_report: PREDICTED. test_calibration_buckets: the 0.7-0.8 bucket holds one split (0 chips) and must show 0 wins
- SE1 / slumbot_exit: PREDICTED. test_unreachable_server_exits_nonzero: every request fails, the session stops early, and the exit code must not be 0
- G1 / import_logs: PREDICTED. test_bare_subcommand_text_does_not_block (the bare pattern matches the dummy process and refuses)
- LK1 / slumbot_luck: PREDICTED. test_split_counts_half: the split hand needs the tie counted half (eq 23/44, adjusted +909.09, not -15454.5)
- G2 / play_match: PREDICTED. test_trap_empty_log_skips_import (the trap imports with an empty log)
