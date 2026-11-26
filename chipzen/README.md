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

Per turn, `bot.py` calls into the C++ engine (`decideFull` in `decide.h`).
The engine runs a Monte Carlo simulation (5000 trials, ~12 ms) of our hand
against a modelled opponent range. It then applies the rules below, top to
bottom, and the first one that fires wins. The GIL is released for the
simulation so the WebSocket heartbeat keeps running.

The equity engine itself is validated by `make test` — see
`tests/test_equity_exact.cpp`, which counts every case the simulator samples.

### 1. Opponent range

The opponent is credited with a fraction of all hands, set by how often they
raised this hand (`villainRangeFraction`).

| Opponent raises this hand | Range (top share of hands) |
|---|---|
| 0 | 100% |
| 1 | 45% |
| 2 | 18% |
| 3 or more | 8% |

The price asked then scales the range. A bet over 75% of the pot before it
multiplies the range by 0.7. A bet under 35% multiplies it by 1.3. The result
stays between 5% and 100%.

Every number here is a hand-fitted prior, not a measurement.

### 2. Memory floor

`opponent.py` counts, per hand, the most raises the opponent made. The floor
is the share of hands in which they made at least this many raises, over
`hands seen + 3`. The range never drops below the floor. An opponent who
raises every hand therefore keeps a wide range, however many times they raise.
Memory resets at each match start.

### 3. Realization discount

Raw equity assumes a free showdown. When we call for a price, equity is
multiplied by a street factor.

| Street | Factor |
|---|---|
| Preflop | 0.85 |
| Flop | 0.82 |
| Turn | 0.90 |
| River | 1.00 |

The discount does not apply when betting, or when the call ends the betting
(all-in, or raising closed). A call needs discounted equity above the pot
odds. A raise is judged on raw equity.

### 4. Actions

| Spot | Rule |
|---|---|
| Stack at 10 bb or less | Raw equity of 55% or more: raise to the max (shove). |
| Small blind, first action, no raise yet | Raw equity of 50% or more: raise to 2.5 bb. |
| Nothing to call | Raw equity of 62% or more: bet 66% of the pot (the discount does not apply when betting). |
| Nothing to call, hopeless hand | Raw equity under 30% and the stack larger than the bet: bet 66% of the pot on a computed share of hands (a bluff). Otherwise check. |
| Facing a bet | Fold if discounted equity is at or below the pot odds. |
| Facing a bet, strong hand | Raw equity of 75% or more: raise. Otherwise call. |

A bet bigger than our stack is treated as a call of the stack, and the excess
leaves the pot. Every raise is clamped to the band the server offered.

Not on this page: a detector for opponent bluffs. It is planned, see #51.

### Known ceilings

All are marked `ponytail:` in the source.

- Every threshold above is fitted by hand. None is solved or learned.
- Realization depends on the street only, not on position or stack depth.
- Short-stack play is a single shove threshold at 10 BB (below 55% equity the normal rules apply), not an ICM
  calculation.
- A shove when checked to at 10 bb is a large overbet. It suits callers and
  not folders.

## Wire contract

What the server sends, observed in 7 live matches on 24 Nov 2026 (logs in
`results/live-logs/`, analysis in `results/2026-11-24-live-log-analysis.md`).
Time limit and turn fixtures come from the SDK's conformance fixtures.

| Topic | What the wire does |
|---|---|
| Hand numbers | `hand_number` is sent on every state. |
| Blinds | Blinds appear in `action_history` as `post_small_blind` and `post_big_blind`. |
| Short blind | A short stack posts a partial all-in blind, e.g. `post_big_blind` 506 when the bb is 600. |
| Labels | Bets and all-ins are both labelled `raise`. |
| `all_in` | Never offered as a valid action in these matches. |
| `max_raise` | The all-in raise-to total. |
| Short stack | `raise` is offered with `min_raise` > `max_raise`. The bot raises exactly `max_raise` (`_raise_band` in `bot.py`). |
| End-of-hand history | The `round_result` history is complete, including folds after our last action. |
| Time limit | `turn_timeout_ms` is 5000. In live match 5 the gap from the STATE line to the decision line over the first 50 decisions was a median of 8 ms (p95 20 ms, max 23 ms) at 5000 trials. |

`bot.py` still handles `all_in` as an offered action (the SDK allows it).

`round_result` carries these fields:

| Field | Content |
|---|---|
| `hand_number` | The hand. |
| `winner_seats` | Seats that won. |
| `pot` | Pot size. |
| `payouts` | Chips paid out. |
| `showdown` | Per seat: `hole_cards`, `hand_rank` (e.g. "High Card", "Pair", "Two Pair", "Straight"), `best_hand` (five cards). |
| `stacks` | Stacks after the hand. |
| `deck_commitment` | Deck commitment. |
| `deck_reveal` | `null`. |

There is no `board` key.

`match_start` lists `seats`. Each seat has `seat`, `is_self`, `display_name`
and `participant_id`.

### Blind schedule

The starting stack is 10,000 chips, which is 100 bb at a bb of 100. The bb
rises every 20 hands.

| Hands | 1-20 | 21-40 | 41-60 | 61-80 | 81-100 | 101-120 | 121-140 |
|---|---|---|---|---|---|---|---|
| bb | 100 | 150 | 200 | 300 | 400 | 600 | 800 |

### What the bot logs

- A version and commit line at match start.
- The `match_start` seats with names.
- One decision line per turn: hand, phase, pot, to_call, bb, raise bounds,
  stack, seat, dealer, history, hole, board, legal actions, range, equity,
  realized, required, action.
- A `round_result` line and a `ROUND` JSON line per hand.
- `STATE` JSON lines for the first 50 decisions.

## Local check

```bash
g++ -std=c++17 -O2 -o /tmp/solver chipzen/solver.cpp \
    montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp \
    model/card.cpp
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

The wire sends `turn_timeout_ms` of 5000 (see Wire contract). An earlier
note put the ranked bot-vs-bot limit at 2000 ms per decision, end to end;
plan against the smaller number. The engine
answers in ~12 ms at 5000 trials, so `POKERCPP_SIMS` has room to rise a long
way if accuracy turns out to matter more than margin. Note the SDK's own
validator warns above 100 ms and uses 500 ms as its reference ceiling, so
staying well under that is the safer target.
