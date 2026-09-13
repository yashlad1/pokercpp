# pokercpp on Chipzen

The C++ Monte Carlo engine plays; Python only carries the wire.

```
chipzen/
  decide.h            decision logic — shared by the module and the CLI binary
  pokercpp_engine.cpp pybind11 wrapper; this is what the bot imports
  solver.cpp          same logic behind a stdin/stdout CLI, for testing
  bot.py              WebSocket adapter and legality clamping
  Dockerfile          two-stage: build the extension, ship a slim runtime
  test_solver.py      drives the CLI binary — no Python deps needed
  test_bot_sdk.py     drives bot.py against the real SDK
```

## Why an extension module, not a subprocess

The sandbox blocks `subprocess` and `ctypes` both, so Python cannot shell
out to a binary or dlopen one. A compiled extension is the supported route —
the SDK's own starter ships its strategy the same way — and it avoids a
process spawn per decision.

## How it decides

Per turn, `bot.py` calls into the C++ engine, which runs a Monte Carlo
simulation (5000 trials, ~12 ms) to get equity, shades it down against the
size of the bet it faces, and compares that to the pot odds. The GIL is
released for the simulation so the WebSocket heartbeat keeps running.

The equity engine itself is validated by `make test` — see
`tests/test_equity_exact.cpp`, which counts every case the simulator samples.

Known ceilings, both marked in the source:

- The opponent is modelled as a uniform random hand. Against a real bot that
  only bets strong hands, raw equity is optimistic; the bet-size discount is
  a flat linear stand-in for a range model.
- Short-stack play is a single push-or-fold threshold at 10 BB, not an ICM
  calculation.

## Local check

```bash
g++ -std=c++17 -O2 -o /tmp/solver chipzen/solver.cpp \
    montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp \
    model/card.cpp model/deck.cpp
python3 chipzen/test_solver.py /tmp/solver
```

## Build and upload

Docker must be running. Build from the repo root, not from `chipzen/`:

Build for **linux/amd64**. The platform runs x86-64, and an arm64 image
built on Apple Silicon will not start there.

```bash
docker build --platform linux/amd64 -f chipzen/Dockerfile -t pokercpp:v1 .
docker save pokercpp:v1 | gzip > pokercpp.tar.gz
ls -lh pokercpp.tar.gz          # upload cap is 250 MB compressed

pip install chipzen-bot
chipzen-sdk validate ./chipzen/ --check-connectivity
```

The validator wants a directory holding the bot and its importable engine.
Running it inside the built image validates the real artifact in its real
environment, which is what actually ships:

```bash
docker run --rm --platform linux/amd64 --entrypoint sh pokercpp:v1 \
    -c "cd /bot && chipzen-sdk validate . --check-connectivity"
```

Then at chipzen.ai: Developer page -> Upload Bot -> accept the rules and
select `pokercpp.tar.gz`. Status moves `uploading -> pending_review ->
reviewing -> active`. Play a free human-vs-bot match before entering a
season — it is the only way to see the decision log.

## Budget

Ranked bot-vs-bot allows 2000 ms per decision, end to end. The engine
answers in ~12 ms at 5000 trials, so `POKERCPP_SIMS` has room to rise a long
way if accuracy turns out to matter more than margin. Note the SDK's own
validator warns above 100 ms and uses 500 ms as its reference ceiling, so
staying well under that is the safer target.
