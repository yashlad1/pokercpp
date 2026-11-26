# No-play-change pin base (kPreflopRealization 0.85)

Base commit: **eb4f96a** (kPreflopRealization 0.85, 26 Nov 2026). The files here are what `tools/pins/capture.sh` wrote for that commit (json, jsonl and txt only; the solver binary and build log are not kept).

## What a pin run executes
- bench.py, 400 hands, 1000 sims, seed0 700001: bot (live wire) and engine, vs aggro / reference / september, stacks 15 / 25 / 100; plus one engine `--no-memory` run (aggro, 25).
- The B4 recipe: bot hero, bench wire, 1000 hands, vs aggro / reference / station, stacks 15 and 100, seed0 700001 and 710001.
- match.py twice (A and B, identical args: bot vs reference, 5 matches, hand cap 100, 1000 sims, seed0 1), then `--compare`; paired.py on the engine aggro-25 pair.
- The CLI solver on the inputs of chipzen/test_solver.py; engine.txt (.so hashes, impl cpu).
- The "september" opponent is c057f40 built once as `pokercpp_engine_base` with its RNG seeded (needs that commit in the checkout's history).

## Exemptions (the whole list)
- `meta.commit` and `meta.coerced` in every .json / .jsonl dump.
- The `engine_so_sha256` and `base_so_sha256` lines of engine.txt (the September build is not byte-reproducible across fresh builds; its play is pinned by the bench dumps vs september).
- `coerced ` lines in .txt stdout.

The B4 dumps from the re-run are compared with this base's own `b4/` files.

## Check a checkout
    PY=/path/to/python tools/pins/check.sh <repo_checkout>
`PY` needs pybind11 and numpy. It prints one PASS/FAIL line per file and `PASS: N checks, 0 failed`; any FAIL exits nonzero. Run one at a time (it uses 4 processes).

## Re-capture
    PY=/path/to/python tools/pins/capture.sh <repo_checkout> <empty_out_dir>
then copy the json, jsonl and txt files here.

## When a new base is needed
Any intended play change (the check then fails by design). Capture at the new commit, commit it as a new dated folder, and point `PINBASE` or the default in check.sh at it.
