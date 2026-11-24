# Code audit and bug hunt, 2026-11-24

A check that the bot works as intended before adding features: data moves correctly, no mistakes, no leaks. Two audits and two deep reviews. Benchmark numbers are in `2026-11-24-bench-results.md`.

## Audit A: the bot against the SDK

**Found**
- The SDK's own NLHE test fixture sends an empty `action_history` on the preflop. The bot derived the big blind from that history, so it read the big blind as 0. If the live server does the same, the small-blind open and the short-stack shove may never have fired, in the current build or in the September build.
- The bot never sent `all_in`. When the legal actions were `["fold", "all_in"]` it would fold.

**Verified**
- Every action the bot returns is legal.
- The raise-to convention matches the SDK.
- Pot and stack meanings match the SDK.
- No exception escapes `decide()`.
- No secrets are logged.

## Audit B: harness and leaks

**Verified**
- Duplicate dealing is real: the same cards with seats swapped on 200 of 200 seeds.
- Chips are conserved: 0 stuck hands.
- Information isolation holds: each player sees only its own cards.
- Opponent memory never crosses matches.
- No secrets in the working tree, the git history, the container image or the tarball.

**Found**
- Match mode capped `to_call` at the stack, so short-stack calls looked cheaper than on the platform. The chips bench was not affected.
- `.gitignore` missed `*.tar.gz` and `.env`.

## Deep reviews

**C++ engine: sound**
- Equities match exact values (AA vs KK 0.826).
- The 169 starting-hand classes are correct.
- Hand evaluator edge cases pass.

**Python side: clean**
- 5,000 fuzzed game states produced 0 illegal actions.
- The SDK validator's full match passes.

**Three engine logic bugs, each reproduced**
- **A1:** the short-stack shove fired when checked to postflop (100 into a 20 pot).
- **A2:** the small-blind open had no "facing only the blind" guard.
- **B:** the opponent's bet size was read against a pot that included the bet. A pot-size bet never narrowed the range, and a half-pot bet widened it.

## Bug table

| # | Bug | Severity | Status | Commit |
|---|---|---|---|---|
| 1 | Big blind read as 0 (empty preflop history) | High | Fixed: blinds read from history, else derived from the first preflop decision | 9636642 |
| 2 | `all_in` never sent | High | Fixed | 9636642 |
| 3 | Match-mode `to_call` cap (bench only) | Medium | Fixed: bench passes `to_call` uncapped, as the platform does | d09e32c |
| 4 | `.gitignore` gaps (`*.tar.gz`, `.env`) | Low | Fixed | d09e32c |
| 5 | A1: short-stack shove when checked to | Medium | Reverted as a trade-off (worse vs station at 8 bb, better vs loosepassive at 8 bb) | none |
| 6 | A2: small-blind open guard | Medium | Fixed, pending commit | none yet |
| 7 | B: bet-size read | Medium | Fixed, pending commit | none yet |
| 8 | Fix 3 (2.5 bb small-blind open) loses to the September bot | Medium | Diagnosed, tuning pending | none yet |
| 9 | `bluffFrequency` not deterministic (about 2% flips on identical input) | Minor | Open | none |
| 10 | Meaning of `max_raise` unconfirmed (raise-to or chips behind) | Unknown | Open | none |

## What was verified as correct

- Legality of every returned action, including 5,000 fuzzed states.
- Raise-to convention, pot and stack meanings.
- Exact equities and the 169-class table.
- Duplicate dealing, chip conservation, information isolation.
- The SDK validator's full match, including connectivity and recovery from a rejected action.
- No secrets in the tree, history, image or tarball.

## Open questions needing a live match

- **Does the server send the blinds in the action history?** The bot now logs `bb=` and `hist=` on each decision, so one free match will settle it.
- Whether `hand_number` is present on every turn.
- Whether no raise is offered against an all-in.
- Whether the server caps `to_call` at the stack.
- Whether there is a separate `all_in` action in the live protocol.
- What `max_raise` means.
