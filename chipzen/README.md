# pokercpp on Chipzen

The C++ Monte Carlo engine plays; Python only carries the wire.

```
chipzen/
  solver.cpp        decision logic — links MonteCarloSimulator + PokerMath
  bot.py            WebSocket adapter, legality clamping, solver supervision
  Dockerfile        two-stage: static C++ build, then a slim runtime
  test_solver.py    self-check against the compiled binary
```

## How it decides

Per turn, `bot.py` sends one line of game state to a long-lived `solver`
process and reads back one action. The solver runs a Monte Carlo simulation
(5000 trials, ~30 ms) to get equity, shades it down against the size of the
bet it faces, and compares that to the pot odds.

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

```bash
docker build -f chipzen/Dockerfile -t pokercpp:v1 .
docker save pokercpp:v1 | gzip > pokercpp.tar.gz
ls -lh pokercpp.tar.gz          # upload cap is 250 MB compressed

pip install chipzen-bot
chipzen-sdk validate ./chipzen/ --check-connectivity
```

Note: the validator's documented usage points it at a directory holding both
the Dockerfile and the bot, and builds with that directory as the context.
This Dockerfile needs the repo root instead, because it compiles `model/` and
`montecarlo/`. If `validate` cannot build it, build the image by hand with the
command above and validate the running container. This is untested here —
Docker was not available on the machine this was written on.

Then at chipzen.ai: Developer page -> Upload Bot -> accept the rules and
select `pokercpp.tar.gz`. Status moves `uploading -> pending_review ->
reviewing -> active`. Play a free human-vs-bot match before entering a
season — it is the only way to see the decision log.

## Budget

Ranked bot-vs-bot allows 2000 ms per decision, end to end. The solver
answers in ~30 ms at 5000 trials, so `POKERCPP_SIMS` has room to rise a long
way if accuracy turns out to matter more than margin.
