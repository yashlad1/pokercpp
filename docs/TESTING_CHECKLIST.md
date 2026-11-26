# Testing checklist: one feature at a time

Rule: one feature per branch and PR. The next feature starts only when every box below is ticked, or marked N/A with a reason, in the PR body. A bench result from the engine alone does not count as tested: the ship candidate has to go through bot.py, match mode and the Docker image.

Paste this list into the PR body. Items marked "(needs #N)" depend on an open PR or issue: tick them once that lands, or mark N/A with the reason.

Run every command from the repo root. `$PY` is a Python with pybind11, pokerkit and chipzen-bot installed.

## 0. Scope
- [ ] Issue with a spec and a "Done when" section
- [ ] Ship candidate named: the exact default values the live bot would run, with no flags

## 1. Unit and black-box tests
- [ ] Black-box test written by someone other than the implementer, from the spec and signatures only
- [ ] Test seen to fail on main's build (paste the output) and passing on the branch
- [ ] Edges covered:
  - [ ] default equals omitted
  - [ ] clamps and floors
  - [ ] boundary values
  - [ ] zero and negative inputs, where the type allows them

## 2. Regression (locally first, then CI)
Build the engine first: `PY=$PY tools/build_engine.sh`

- [ ] `make test`
- [ ] `make test-asan`
- [ ] `make strict` (CI runs `make strict CXX=clang++`)
- [ ] `python chipzen/test_solver.py /tmp/solver` (build the solver first, see Commands)
- [ ] `python chipzen/test_engine_seed.py`
- [ ] `python chipzen/test_preflop_realization.py`
- [ ] `python tools/test_paired.py`
- [ ] `PYTHONPATH=chipzen python chipzen/test_bot_sdk.py`
- [ ] `PYTHONPATH=chipzen python chipzen/test_replay.py`
- [ ] `PYTHONPATH=chipzen POKERCPP_SIMS=2000 python chipzen/test_v4.py`
- [ ] `python chipzen/test_logging.py`
- [ ] CI green on the PR: the C++ jobs (Build and test, Strict warnings, ASan + UBSan)
- [ ] CI green on the PR: the bot job

## 3. Live play unchanged when a feature is off (flagged features)
- [ ] Default build against main: the `results` arrays are identical
  - opponents: aggro, reference, station
  - stacks: 15 and 100 bb
  - seed0: 700001 and 710001
  - compare the `results` arrays only; the dump files also carry knob keys

## 4. The real bot path, on the ship candidate
- [ ] Build with the new default value, no flags
- [ ] `bench.py --hero bot`, paired against main's build:
  - [ ] every registered opponent (`--vs all`)
  - [ ] 15, 25 and 100 bb (`--stack 15`, `--stack 25`, `--stack 100`)
  - [ ] 2000 pairs (`--hands 4000`)
  - [ ] two seed sets
  - [ ] any significant loss flagged in the PR
- [ ] `test_bot_sdk.py` on the candidate: 0 illegal actions, worst latency under the limit
- [ ] Replay of live turn states on the candidate

## 5. Tournament format
- [ ] `tools/match.py` freezeouts with rising blinds, candidate against main
  - [ ] live blind schedule (needs #89; the schedule in match.py is a placeholder)
  - [ ] paired McNemar test on match wins (`match.py --dump`, then `--compare A B`; #61)

## 6. Pre-registration and records
- [ ] Decision rule and exact commands committed before any run
- [ ] `results/<date>-<slug>.md` written (no personal details)
- [ ] Rows added to `results/eval-log.xlsx` with `tools/evlog.py`
- [ ] Vault status line updated

## 7. Package
- [ ] Docker image builds:
  - [ ] `tools/docker_local.sh` locally (arm64, also runs test_bot_sdk.py and test_v4.py inside)
  - [ ] the upload image as the Dockerfile builds it (linux/amd64)
- [ ] `chipzen-sdk validate` inside the image: all checks pass (the os-import warning is known)
- [ ] Container smoke test: none yet (no script in tools/ runs the amd64 image end to end; `tools/docker_local.sh` is the nearest, and it is arm64)

## 8. Ship (owner only)
- [ ] Tag the commit
- [ ] Keep the previous image tarball for rollback
- [ ] Upload
- [ ] First live match log checked: 0 illegal actions, wire fields logged

## Commands
Each one was checked against the Makefile, ci.yml, argparse in tools/*.py, tools/*.sh or chipzen/README.md.

```
PY=$PY tools/build_engine.sh
make test
make test-asan CXX=clang++
make strict CXX=clang++
g++ -std=c++17 -O2 -o /tmp/solver chipzen/solver.cpp montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp
python chipzen/test_solver.py /tmp/solver
python chipzen/test_engine_seed.py
python chipzen/test_preflop_realization.py
python tools/test_paired.py
PYTHONPATH=chipzen python chipzen/test_bot_sdk.py
PYTHONPATH=chipzen POKERCPP_SIMS=2000 python chipzen/test_v4.py
python chipzen/test_logging.py
PYTHONPATH=chipzen python chipzen/test_replay.py
$PY tools/bench.py --hero bot --vs all --stack 15 --hands 4000 --seed0 700001 --dump out.json
$PY tools/bench.py --vs aggro --stack 100 --hands 1000 --seed0 710001 --dump out.json
$PY tools/paired.py A.json B.json
$PY tools/match.py --matches 200 --vs maniac --hero bot --seed0 1
$PY tools/evlog.py paired results/eval-log.xlsx A.json B.json --experiment X --comparison "..." --build-a ... --build-b ... --logic "..."
tools/docker_local.sh
docker build --platform linux/amd64 -f chipzen/Dockerfile -t pokercpp:v1 .
docker save pokercpp:v1 | gzip > pokercpp.tar.gz
docker run --rm --platform linux/amd64 --entrypoint sh pokercpp:v1 -c "cd /bot && chipzen-sdk validate . --check-connectivity"
```

Notes:
- `bench.py --stack` is the stack in big blinds; `--hands 4000` is 2000 pairs (each seed is played in both seat orders).
- `bench.py` and `match.py` import the engine from `chipzen/`. To compare two builds, build each in its own checkout (or worktree) and run each one's `--dump` file through `tools/paired.py`.
- `match.py` has no build-versus-build option and no `--dump` flag today (`tools/evlog.py match` expects one); the freezeout comparison of candidate against main is partly manual until #61 lands.
