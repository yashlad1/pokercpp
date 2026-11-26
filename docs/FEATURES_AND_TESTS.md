# Features and tests

This is the per-feature map of the Chipzen bot: what each behaviour is, which test covers it, what could break without a test failing, and which tests to add.

`docs/TESTING_CHECKLIST.md` (PR #100) is the per-change process: what to run before a change merges. This file is the other axis: given a feature, what protects it. Use the checklist to ship a change and this file to find holes.

Read it as of origin/main at c3a887b (2026-11-25), with every file:line reference refreshed on 2026-11-26 to the tree after the deslop refactor (local CLI game and its dead code removed). PR #100 (838976d) changed only `ci.yml` and the checklist after it.

## Conventions

- **Added**: the first commit that introduced the identifier (`git log -S`), or the PR/issue. A star means added on 2026-11-25: preflop-only realization (#97, PR #98), `--preflop-realization`, the CI bot job (#92) and its tests, the replay test (#87), the decide-properties test.
- **CI?** is read from `.github/workflows/ci.yml` on origin/main. Jobs: `test` (`make test`), `strict`, `sanitizers` (`make test-asan`), `bot` (solver, SDK, v4, logging, engine seed, replay, preflop realization, paired). PR #100 added the last two.
- Files in the table headers: `decide.h` = `chipzen/decide.h`, `bot.py` = `chipzen/bot.py`, `solver` = `chipzen/test_solver.py`, `sdk` = `test_bot_sdk.py`, `v4` = `test_v4.py`, `props` = `tests/test_decide_properties.cpp`.
- Test cost: **cheap** = under a minute, runs in CI. **bench** / **match** = needs bench or match time, not CI.
- On main, every existing test passed when run for this document (see the end).

## 1. Decisions (`decide.h`, `pokercpp_engine.cpp`)

| ID | Feature | Where | Added | Existing tests (CI?) | Gap | Tests to add |
|---|---|---|---|---|---|---|
| D1 | Opponent range by raise count: 100% / 45% / 18% / 8%, floor 5% | decide.h:52-67 | 39ae255 | solver loose vs tight, props range monotonic (yes) | Exact cut values and the 0.05 floor not pinned | Cheap unit: `villainRangeFraction(0..3,0,0)` equals 1.0/.45/.18/.08; huge raises gives 0.05 |
| D2 | Bet-size factor: bet over 75% of the pot-before x0.7, under 35% x1.3 | decide.h:58-63 | e1d32bd | solver pot-size case, props price band (yes) | The 0.35 and 0.75 edges and 1.3 factor untested | Cheap unit: bet 0.34/0.35/0.75/0.76 of pot gives expected factor |
| D3 | Realization by street: preflop 0.75, flop 0.82, turn 0.90, river 1.0 | decide.h:76-83 | 39ae255 | preflop test: flop 0.82, preflop 0.75 (yes) | Turn 0.90 and river 1.0 never asserted | Cheap unit: `realized/equity` ratio on turn and river spots; add to the CI bot job |
| D4 | Preflop-only realization setting, default 0.75 (`kPreflopRealization`) | decide.h:69,191 | * #97, PR #98 | `test_preflop_realization.py`: default equals 0.75, ratio, flop ignores it, TT fold flips (yes) | Live bot never passes it, so only the default matters live (W18) | None beyond D3; strength measured in #81/#82 |
| D5 | Realization scale and bluff on/off knobs, defaults match shipping | decide.h:189 | 42d8d18 | props and solver use defaults only (yes) | Non-default knobs only used by bench; default equal to omitted not tested | Cheap unit: explicit defaults equal omitted args on 5 spots |
| D6 | Call that ends the betting uses raw equity (to_call >= stack or max_raise <= 0) | decide.h:206-209 | 50b3d53 | solver ENDS (all-in call, closed raise, control that folds) (yes) | Boundary `toCall == stack` exactly, and `max_raise == 0` with stack deep | Cheap unit: to_call = stack and stack+1 give same action; max_raise 0 vs 1 differ |
| D7 | Cap to_call at our stack, cut pot by the excess | decide.h:193 | 4e686ba | solver CAP: over-report equals capped (yes) | `stack == 0` skips the cap; negative to_call not tried | Cheap property: random to_call above stack gives identical Decision |
| D8 | Short-stack shove at 10bb or less with equity 0.55 or more | decide.h:216-221 | f697b12 | solver short monster shoves, shove allowed facing a bet (yes) | 10.0 vs 10.1bb edge, 0.55 edge, `bb == 0` (100bb default) | Cheap unit: stack 10bb vs 10.1bb same hand; bb=0 spot does not shove |
| D9 | Small-blind open to 2.5bb with equity 0.50 or more | decide.h:172-181,223-230 | 42d8d18, guard e1d32bd | solver OPEN (K9o opens, AA same size, 72o no, 10bb shove) and A2 no-open guard (yes) | `OPEN_EQ` edge, open size above max_raise, open when `bb == 0` | Cheap unit: open clamps to max_raise; equity just under 0.50 no raise |
| D10 | Checked-to value bet: 0.66 pot when shaded equity is 0.62 or more | decide.h:232-239 | early (not traced) | solver nut flush bets, nuts always bets (yes) | 0.62 and 0.66 constants not pinned | Cheap unit: nuts spot raises to `int(pot*0.66)` exactly |
| D11 | Polarised bluff: equity under 0.30, frequency from range composition, card-hash draw | decide.h:92-160,245-253 | edd1a99 | solver air bets sometimes not always, same spot same answer, bet never above stack (yes) | Frequency maths (`bluffShare`, `bluffFrequency`) untested; 0.30 edge; bluff flag | Cheap unit: `bluffShare(100,50)=0.25`; frequency in [0,1], 0 when no air. Bench: no-bluff vs shipping |
| D12 | Fold when shaded equity does not beat pot odds | decide.h:259 | early (not traced) | solver trash folds, 72o folds big bet (yes) | Equal-to-price edge; fold vs call near the line unpinned | Cheap property: price sweep never turns fold into call (props has it) plus an edge case |
| D13 | Raise when raw equity 0.75 or more: `0.75*(pot+to_call)+to_call`, banded | decide.h:261-266 | 39ae255 | solver AA raises within band (yes) | Sizing formula not asserted | Cheap unit: AA facing 100 into 300 raises to the formula value |
| D14 | `boundedRaise`: clamp to band, 0 when either bound is 0 | decide.h:44-47 | f697b12 | solver closed raise gives no raise (yes) | min greater than max case; negative inputs | Cheap unit: (50, 100, 80), (50, 0, 0), (50,-1,10) |
| D15 | `range_floor`: widen range to opponent's observed raise rate | decide.h:195 | fe0f423 | v4 T9 via bot (yes) | No engine-level test with floor above the step value | Cheap black-box: same spot, floor 0 vs 0.6 shifts `range` and fold/call |
| D16 | `seed`: repeatable Monte Carlo, 0 means fresh | decide.h:199,141 | 42d8d18 | `test_engine_seed.py` (flop, river bluff path) (yes) | Seed through `bluffFrequency` inner sims only covered on one spot | Cheap: run each solver spot twice with a seed, compare |
| D17 | Engine wrapper: card parse, 2 hole cards, sims 0 means 5000, GIL release | pokercpp_engine.cpp:15-72, decide.h:15-41 | f697b12 | solver malformed line; none for bad card strings in the module (partly) | Bad card, 1 hole card, duplicate cards, `sims <= 0` untested | Cheap black-box: each raises `ValueError`/`invalid_argument`; `sims=0` works |
| D18 | Metal GPU equity path (local only) | decide.h:132-154 | 165f4d7 | `tools/test_metal.mm`, manual (no) | GPU result vs CPU result drift; not in image | Manual: build `--metal`, compare equity to CPU within error. Never in CI |
| D19 | CLI solver line protocol used by tests | chipzen/solver.cpp | 3e22a0f | `test_solver.py` (yes) | Reply format for fold/check/call/raise only through the tests | None needed |

## 2. Wire adapter (`bot.py`)

| ID | Feature | Where | Added | Existing tests (CI?) | Gap | Tests to add |
|---|---|---|---|---|---|---|
| W1 | `_villain_raises`: count raise/bet/all_in by non-us seats, skip blinds | bot.py:50-58 | 39ae255 | Only indirectly via v4 T9, T10 (yes) | A renamed wire action (`bet_to`, `shove`) silently gives 0 raises | Cheap unit: histories with every action name, own seat, post_ entries, missing seat |
| W2 | `_current_blinds`: read sb/bb off synthetic history entries, stop at first real action | bot.py:61-72 | 3e22a0f | v4 T1-T3 (yes), replay checks bb (yes) | Ante entries mid-list, missing amounts, bb before sb order | Cheap unit: ante then blinds; blinds only; empty history |
| W3 | `_bb`: four-step big-blind read, cached per hand | bot.py:148-186 | 9636642, a12af80 | v4 T1,T2,T3,T4,T8; replay on 325 live states (yes) | Antes (`self.ante`) and hand_number reuse untested; one live day only | Cheap unit: ante 10 game_config; new hand_number after fixed bb. Replay: add a newer fixture each match day |
| W4 | `BB MISMATCH` warning, logged only | bot.py:172-180 | a12af80 | v4 T5 (yes) | Warning is never asserted to be harmless on live data | Cheap: replay asserts no MISMATCH warnings on the fixtures |
| W5 | `_raise_band`: min above max collapses to max (short stack) | bot.py:75-80 | e9bf4bc | v4 T10 (yes) | Case with "raise" absent, or max 0, untested | Cheap unit: (min=400,max=300), (0,0), (200,0), no raise in valid |
| W6 | Raise at max, or raise offered only as all_in, becomes `Action.all_in()` | bot.py:265-282 | 9636642 | sdk "only all_in raises" and 80 or all_in (yes) | Target exactly at hi with `all_in` absent from valid | Cheap black-box: target equals hi, valid has raise but no all_in: must be `raise_to(hi)` |
| W7 | Call offered only as all_in becomes all_in | bot.py:286-287 | 9636642 | sdk "call offered only as all_in" (yes) | Unknown action word from engine | Cheap unit: engine reply `call` with valid `[fold, all_in]` |
| W8 | Legality fallbacks: `_safe_default`, fold becomes check when free | bot.py:253-297 | 3e22a0f | sdk all spots legal, solver (yes) | `_safe_default` returns `fold` even if not in valid; no test of odd valid sets | Cheap property: for every subset of valid actions, result is in the subset or reported |
| W9 | Engine exception falls back to check/fold, logs `ENGINE FAILED` | bot.py:226-229 | b873caa | `tools/fuzz_bot.py` counts exceptions, illegal actions, ENGINE FAILED; manual (no) | No test in CI; fuzz is the only coverage | Cheap black-box: monkeypatch engine to raise; assert check or fold and log line |
| W10 | `hand_number` or `_round_seq` keys opponent memory | bot.py:90,104,116-118,210 | a12af80 | v4 T2, T3, T8, T9 (hand_number 0) (yes) | Collision when both exist and differ | Cheap unit: two matches, memory resets; mixed hand_number 0 and real |
| W11 | Match reset: new Opponent, blinds, STATE counter | bot.py:100-114 | fe0f423, a12af80 | v4 T6 (STATE counter), T9 (yes) | Opponent reset between matches not asserted directly | Cheap unit: raise history, `on_match_start`, `range_floor` is 0 |
| W12 | STATE log: raw GameState json, capped at 50 per match | bot.py:31,188-196 | a12af80 | v4 T6 (yes) | A non-serialisable field would be swallowed with a log line | Cheap: replay log parse of every field type |
| W13 | Decision log line: hand, bb, hist, hole, board, legal, equity, action | bot.py:232-250 | b873caa, 199d5b8 | logging spec3 board and hole (yes) | `_hist` fallback `?`, None fields, format crash outside try | Cheap fuzz: states with None pot/stack/history must not raise |
| W14 | ROUND json with showdown cards, stacks, payouts, no action_history | bot.py:125-146 | 252038d | logging spec2 (yes) | `round_result` without `result`, bad types | Cheap: covered for None; add list-valued showdown with nulls |
| W15 | Version and commit stamp at start and match start | bot.py:30,106,305 | a12af80 | v4 T7, logging spec1 (yes) | `VERSION` not tied to a release tag | Cheap: assert `VERSION` string matches Dockerfile label if one is added |
| W16 | Env handling: `CHIPZEN_WS_URL` required (exit 2), `POKERCPP_SIMS` | bot.py:35,300-325 | 3e22a0f | v4 T7 exit code 2 (yes) | `POKERCPP_SIMS` junk value crashes import | Cheap unit: `POKERCPP_SIMS=abc` import behaviour decided and tested |
| W17 | Latency: no guard in code, fixed 5000 sims (~12ms) | bot.py:35 | f697b12 | sdk prints worst latency; replay asserts under 100ms per state (yes) | Measured on dev Mac, not in the amd64 alpine image | Image: time 200 decisions inside the built image. Match |
| W18 | Pass-through of engine settings: bot passes only `range_floor`, `villain_raises`, sims | bot.py:211-225 | fe0f423 | None direct; bench `--hero bot` (no) | Preflop realization is not wired from bot; live uses the default | Cheap: assert `bot.decide` result equals engine call with defaults on a fixture |
| W19 | Turn counter for the round_result log | bot.py:122-123,146 | 252038d | none (no) | Cosmetic only | None needed |

## 3. Opponent memory (`opponent.py`)

| ID | Feature | Where | Added | Existing tests (CI?) | Gap | Tests to add |
|---|---|---|---|---|---|---|
| O1 | Most raises seen per hand | opponent.py:19-20 | fe0f423 | v4 T9 via bot (yes) | No direct unit test; hand with no sightings | Cheap unit: `saw` twice same hand keeps max; new hand adds an entry |
| O2 | `range_floor`: hands with at least k raises over (hands + 3) | opponent.py:22-27 | fe0f423 | v4 T9: 20 shoves flip K8o fold to call (yes) | `PRIOR_HANDS=3`, k above 1, zero hands, k below 1 | Cheap unit: after 0, 1, 20 hands floor equals expected fraction; k=0 gives 0.0 |
| O3 | Per-match reset | bot.py:101 | fe0f423 | v4 T9 uses fresh bots only (yes) | Not tested across matches in one process | Cheap: see W11 |
| O4 | Value of the floor in play: widens range only against aggressive opponents | opponent.py:4-11 | fe0f423 | bench vs maniac and nit (no) | Whether it helps is only a bench result | Bench-paired: `--no-memory` vs shipping vs maniac and nit |

## 4. Packaging (Docker image, validator)

| ID | Feature | Where | Added | Existing tests (CI?) | Gap | Tests to add |
|---|---|---|---|---|---|---|
| P1 | Two-stage build, engine compiled to `.so` in stage one | chipzen/Dockerfile:9-29 | f697b12 | `tools/docker_local.sh` runs sdk and v4 in a local arm64 image (no) | CI never builds the image | Image: `docker build --platform linux/amd64`, then import `pokercpp_engine` and run sdk test inside |
| P2 | Pinned `chipzen-bot==0.7.1` | Dockerfile:41 | 4e686ba | CI installs same pin (yes, but not from the Dockerfile) | The Dockerfile pin and the CI pin can drift | Cheap: CI step greps both pins and compares |
| P3 | Static libstdc++, strip, musl base | Dockerfile:19-29 | f697b12 | none (no) | Runtime `.so` missing a library only shows in the image | Image: `ldd` the `.so` in the final stage |
| P4 | COPY list: bot.py, opponent.py, Dockerfile, .dockerignore | Dockerfile:45-47 | 4e686ba, fe0f423 | none (no) | A new bot module not added to COPY fails at import in the container | Image: `python -c "import bot"` in the final image; cheap grep that every `import` in `bot.py` is copied |
| P5 | Non-root user, `POKERCPP_COMMIT` from `GIT_SHA` | Dockerfile:49-53 | 3e22a0f, a12af80 | v4 T7 reads env, not the image (no) | Image does not stamp the sha unless built with the arg | Image: build with `--build-arg GIT_SHA=x`, run to exit 2 and read the log line |
| P6 | Platform validator `chipzen-sdk validate .` | outside repo | 4e686ba | none in repo (no) | Run by hand; validator version changed once | Manual before upload: run the validator on the bot folder |
| P7 | amd64 target (platform runs x86-64); local build is arm64 | Dockerfile:5-9 | 3e22a0f | none (no) | An arm64 image cannot start on the platform | Image: check `docker inspect` arch is `amd64` before upload |
| P8 | CI engine build differs from the image (g++ glibc, Python 3.13 vs alpine, 3.11) | ci.yml bot job | * #92 | CI bot job (yes) | CI passing says nothing about the alpine build | Image: run one SDK test in the final image |

## 5. Tooling

| ID | Feature | Where | Added | Existing tests (CI?) | Gap | Tests to add |
|---|---|---|---|---|---|---|
| T1 | `bench.py`: duplicate-dealt bench over pokerkit, bb/100 with 95% CI | tools/bench.py:490-597 | c057f40 | none direct; `--hero bot` exercises the adapter (no) | Engine game rules (min raise after all-in, side pots) trusted | Cheap: tiny pokerkit hand with known result; bench 20 hands smoke |
| T2 | Bench knobs: `--hands --sims --vs --ab --bb --stack --seed0 --hero --history --hand-number --realization-scale --no-bluff --no-memory --dump` | tools/bench.py:641-666 | c057f40, 42d8d18 | none (no) | Flag misuse rejected only by argparse checks | Cheap: `--dump` with `--vs all` errors; `--hero bot` with knobs errors |
| T3 | `--preflop-realization` flag | tools/bench.py:661 | * 64b9342 (#97, #81) | none (no) | Flag value reaching the engine unchecked | Cheap: 4-hand run with 0.75 equals no flag; bench-paired 0.75 vs 0.95 |
| T4 | `paired.py`: per-pair difference of two dumps with 95% CI | tools/paired.py | 42d8d18 | `tools/test_paired.py` (yes) | None | None |
| T5 | `match.py`: freezeout matches, rising blinds, scored by wins | tools/match.py | c080980 | none (no) | Assumed blind schedule, not Chipzen's | Match: 20-pair smoke vs nit; check winner count and hand cap |
| T6 | `evlog.py`: xlsx eval log appender | tools/evlog.py | 46b763b | none (no) | Wrong row or CI maths goes into the permanent log | Cheap: append a known dump pair to a temp xlsx, read back |
| T7 | `build_engine.sh` (default, native, `--metal`) | tools/build_engine.sh | d350b5f | CI runs it with `PY=python` (yes) | `native` and `--metal` modes not run in CI | Cheap local: run `native` once per release |
| T8 | `docker_local.sh`: arm64 image plus sdk and v4 tests | tools/docker_local.sh | d350b5f | none (no) | Runs only on the owner's Mac | Image, manual before each upload |
| T9 | `fuzz_bot.py`, `import_logs.py`, `play_match.sh`, `run_live.sh` | tools/ | 0ec5741, 41c0881, ca65053, 8e53764 | none (no) | Fuzz script is the only crash test of `decide` and is manual | Cheap: run `fuzz_bot.py` in CI for 200 states |
| T10 | Replay test on logged live states | chipzen/test_replay.py, fixtures | * #87, 58316a8 | `test_replay.py`: legal action, raise in band, bb matches, no ENGINE FAILED, under 100ms (yes) | One fixture day, 325 states, 96% same action (informational) | Cheap: add a fixture per match day, esp. one with antes and short stacks |
| T11 | CI bot job | .github/workflows/ci.yml:44-119 | * #92 | self (yes) | Not run on the image | Image: see P1 |
| T12 | Testing checklist | docs/TESTING_CHECKLIST.md | * PR #100 | n/a | Process only | None |
| T13 | Decide properties: x10 chip scaling, price monotone, range monotone | tests/test_decide_properties.cpp | * 93aaad0 (#66) | `make test`, `make test-asan` (yes) | Properties cover decide.h only, not bot.py | Cheap: add a property for `_to_action` legality |

## Priority gaps

1. **Engine exception fallback (W9) has no CI test.** `tools/fuzz_bot.py` exercises it by hand only. If the engine throws (bad card string, a card repeated, a missing hole card), the bot plays check/fold for the match. `_safe_default` returns `fold` even when `fold` is not in `valid_actions`. Cheap black-box test: patch the engine to raise, assert a legal action for several `valid_actions` sets.
2. **No latency guard (W17).** `bot.py` has none. Timing was only measured on the dev Mac (median 1.3ms, max 12ms). Nobody has timed it in the amd64 alpine image. A slow host could exceed the 2000ms budget. Image-level timing test needed.
3. **The image is never built in CI (P1-P5, P8).** The image (python:3.11-alpine, musl) differs from the CI's Python 3.13 on glibc. A missing file in the `COPY` list or a missing library only shows up after upload. Build the image and import the bot in it.
4. **Villain raise counting (W1) is only tested indirectly.** If Chipzen renames or adds an action word, `villain_raises` becomes 0, the range stays at 100% and no test fails. Add a unit test for every action name and the replay fixtures.
5. **Raise band and odd valid-action sets (W5, W6, W8).** Tests cover min above max and all_in-only. Not covered: raise listed but both bounds 0, raise at the cap with no `all_in`, a `valid_actions` set with neither fold nor check. Any of these is an illegal action in a live match. Add a property test over subsets of `valid_actions`.
6. **Big-blind read (W3) under antes and escalating blinds.** One live fixture day. `self.ante` subtraction and the 3rd-step derivation have no ante test. A wrong bb moves the short-stack shove zone and the 2.5bb open.
7. **Opponent memory (O1, O2) has no direct unit test.** One test (v4 T9) covers it through the bot. `PRIOR_HANDS=3`, the max-per-hand rule and the reset between matches can change without a failure.
8. **Decision constants are unpinned (D1-D3, D10, D13).** The 0.62 value bet, 0.66 sizing, 0.75 raise equity, and the turn 0.90 and river 1.00 realization could change with no test failing. Only a bench would notice. Add exact-value unit tests.
9. **`POKERCPP_SIMS` with a non-number crashes at import (W16).** That would fail before the first hand. Decide the behaviour and test it.

## Test run on main

All existing tests passed on origin/main (c3a887b) in this worktree, using a local g++/clang++ build: `make test`, solver, SDK (worst latency 3.6ms), v4, logging, engine seed, replay (325 states, 8 matches, median 1.3ms, max 12.1ms), preflop realization, `tools/test_paired.py`. `test_engine_seed.py` was run directly because the venv has no pytest (CI installs it).
