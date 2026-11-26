# pokercpp: a heads-up no-limit hold'em bot

A heads-up no-limit Texas Hold'em bot for the Chipzen platform. The decisions come from a Monte Carlo equity engine in **C++17**, compiled into a Python extension; a thin Python adapter speaks the wire protocol and checks that every action is legal.

---

## Chipzen bot

- **What it is:** the decision logic in `chipzen/decide.h` is compiled into a Python extension, and `chipzen/bot.py` handles the wire protocol and checks that every action is legal.
- **Build, validate and upload:** [chipzen/README.md](chipzen/README.md).
- **Offline measurement:**
  - `tools/bench.py`: duplicate-dealt bb/100 against scripted opponents, seeded and repeatable; `--hero bot` runs the real `chipzen/bot.py`.
  - `tools/paired.py`: the paired difference between two builds, from `bench.py --dump` files.
  - `tools/match.py`: freezeout matches with rising blinds, scored by match wins.
- **Tests:** `make test` (C++ engine), `chipzen/test_solver.py` (decision rules through the CLI solver), `chipzen/test_bot_sdk.py` (bot.py against the real SDK), `chipzen/test_engine_seed.py` and `tools/test_paired.py`.
- **Results:** write-ups of the benchmark runs in [results/](results/).
- **What to run and what protects what:** [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) and [docs/FEATURES_AND_TESTS.md](docs/FEATURES_AND_TESTS.md).

---

## Engine

| Path | What it is |
|---|---|
| `model/card.*` | Card, suit and rank |
| `model/advanced_hand_evaluator.*`, `model/fast_eval.h`, `model/hand_types.h` | Best five of seven with full kicker resolution |
| `model/poker_math.h` | Pot odds and related helpers |
| `montecarlo/MonteCarloSimulator.*` | Win probability by dealing out the unknown cards many times and evaluating each board with the same evaluator |
| `chipzen/decide.h` | The decision rules built on that equity |

The equity model assumes a **uniformly random opponent hand**, which overstates equity by roughly 13 percentage points against a tight range. See `docs/MONTE_CARLO_ANALYSIS.md`.

---

## Build and test

Requires **clang++** (or g++) with C++17.

```bash
make test        # hand evaluator, Monte Carlo, exact equity, decide properties, exhaustive evaluator
make test-asan   # the same tests under AddressSanitizer and UBSan
make strict      # compile the engine with the noisier warning set
```

The rules of the game are in `res/texashold.md`.

---

## License

PolyForm Noncommercial 1.0.0 (SPDX: PolyForm-Noncommercial-1.0.0). Noncommercial use and sharing are allowed; entering the code or a derivative in a prize competition is not licensed. See LICENSE.md.
