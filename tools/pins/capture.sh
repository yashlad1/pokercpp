#!/bin/bash
# Capture the no-play-change pin set of a repo checkout.
#   PY=<python with pybind11 + numpy> capture.sh <repo_checkout> <out_dir>   (out_dir must not exist or be empty)
# Optional: PIN_BASE_ENGINE=<dir> caches the September engine build (default: $TMPDIR/pokercpp-pin-base-engine).
# Builds a copy of the repo's code dirs (the working tree, not the commit) in a
# staging dir next to out_dir, so <repo_dir> itself is never touched. Writes:
#   bench/*.json,txt   bench.py dumps: bot live + engine x stacks 15/25/100 x 3 opponents (+1 --no-memory dump)
#   b4/*.json,txt      the B4 baseline recipe, re-run
#   match-{A,B}.jsonl  tools/match.py dumps;  match-*.txt, match-compare.txt, paired.txt
#   solver.txt         solver CLI replies on test_solver.py's inputs
#   engine.txt         .so sha256 and impl
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
: "${PY:?set PY to a python with pybind11 and numpy}"
[ $# = 2 ] || { echo "usage: $0 <repo_dir> <out_dir>" >&2; exit 2; }
repo=$(cd "$1" && pwd)
MAIN=$repo   # the checkout needs c057f40 in its history (not a shallow clone)
mkdir -p "$2"
out=$(cd "$2" && pwd)
[ -z "$(ls -A "$out")" ] || { echo "out_dir not empty: $out" >&2; exit 2; }
stage="$out.stage"
mkdir -p "$stage" "$out/bench" "$out/b4"

# September (c057f40) as pokercpp_engine_base: built once, shared by every run so its bytes never vary.
# That build takes no seed and draws from random_device, so its bench runs differ every time. The sed below
# replaces that one RNG source with a fixed-seed generator (strategy untouched), making September's runs repeatable.
BASE=${PIN_BASE_ENGINE:-${TMPDIR:-/tmp}/pokercpp-pin-base-engine}
if ! ls "$BASE"/pokercpp_engine_base*.so >/dev/null 2>&1; then
  mkdir -p "$BASE" "$BASE/src"
  git -C "$MAIN" archive c057f40 chipzen montecarlo model | tar -x -C "$BASE/src"
  sed -i '' 's/PYBIND11_MODULE(pokercpp_engine,/PYBIND11_MODULE(pokercpp_engine_base,/' "$BASE/src/chipzen/pokercpp_engine.cpp"
  sed -i '' 's/std::random_device rd;/static std::mt19937 pinseed(20251126);/; s/std::mt19937 g(rd());/std::mt19937 g(pinseed());/' "$BASE/src/montecarlo/MonteCarloSimulator.cpp"
  grep -q pinseed "$BASE/src/montecarlo/MonteCarloSimulator.cpp" && ! grep -q 'random_device rd' "$BASE/src/montecarlo/MonteCarloSimulator.cpp"
  EXT=$("$PY" -c 'import sysconfig;print(sysconfig.get_config_var("EXT_SUFFIX"))')
  (cd "$BASE/src" && clang++ -std=c++17 -O2 -shared -fPIC -undefined dynamic_lookup $("$PY" -m pybind11 --includes) \
    chipzen/pokercpp_engine.cpp montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp \
    -o "$BASE/pokercpp_engine_base$EXT")
fi

rsync -a --exclude='*.so' --exclude=__pycache__ --exclude=.DS_Store \
  "$repo/chipzen" "$repo/montecarlo" "$repo/model" "$repo/tools" "$stage/"
cd "$stage"
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$stage/chipzen:$BASE"

# CPU engine (no --metal), and the CLI solver the way CI builds it
PY=$PY tools/build_engine.sh >"$out/build.log" 2>&1
g++ -std=c++17 -O2 -o "$out/solver" chipzen/solver.cpp montecarlo/MonteCarloSimulator.cpp \
  model/advanced_hand_evaluator.cpp model/card.cpp >>"$out/build.log" 2>&1

# bench jobs: "<out path without ext> <bench.py args>"
{
  for o in aggro reference september; do for s in 15 25 100; do
    c="--vs $o --stack $s --hands 400 --sims 1000 --seed0 700001"
    echo "bench/bot-live-$o-$s --hero bot --wire live $c"
    echo "bench/engine-$o-$s --hero engine $c"
  done; done
  echo "bench/engine-nomemory-aggro-25 --hero engine --no-memory --vs aggro --stack 25 --hands 400 --sims 1000 --seed0 700001"
  # B4 recipe (results/2026-11-25-phase-b.md, B4; the loop of the b4 dumps script): bot hero, bench wire, 1000 hands, 2000 sims
  for o in aggro reference station; do for s in 15 100; do for d in 700001 710001; do
    echo "b4/$o-$s-$d --hero bot --wire bench --vs $o --stack $s --seed0 $d --hands 1000"
  done; done; done
} > "$out/jobs.txt"

runjob() {
  n=$1; shift
  "$PY" tools/bench.py "$@" --dump "$out/$n.json" >"$out/$n.txt" 2>&1 || echo "$n" >>"$out/FAILED"
}
export -f runjob; export PY out
xargs -P 4 -L 1 bash -c 'runjob "$@"' _ <"$out/jobs.txt" &
JOBS=$!

# match.py: two identical runs (A/A), then --compare; then paired.py
M="--hero bot --wire live --vs reference --matches 5 --hand-cap 100 --sims 1000 --seed0 1"
for x in A B; do
  "$PY" tools/match.py $M --dump "$out/match-$x.jsonl" >"$out/match-$x.txt" 2>&1 || echo match-$x >>"$out/FAILED"
done
"$PY" tools/match.py --compare "$out/match-A.jsonl" "$out/match-B.jsonl" >"$out/match-compare.txt" 2>&1 || echo match-compare >>"$out/FAILED"

# solver CLI on test_solver.py's own input lines
"$PY" "$HERE/solver_trace.py" "$out/solver" chipzen/test_solver.py >"$out/solver.txt" 2>&1 || echo solver >>"$out/FAILED"

wait $JOBS || true
"$PY" tools/paired.py "$out/bench/engine-aggro-25.json" "$out/bench/engine-nomemory-aggro-25.json" >"$out/paired.txt" 2>&1 || echo paired >>"$out/FAILED"
grep -q '^A - B: .* \(better\|worse\|inconclusive\)$' "$out/paired.txt" || echo paired-verdict >>"$out/FAILED"

# engine identity and impl: every dump must say meta.impl == "cpu"
"$PY" - "$out" >"$out/engine.txt" <<'E' || echo engine >>"$out/FAILED"
import glob, hashlib, json, sys, pokercpp_engine, pokercpp_engine_base
out = sys.argv[1]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
impls = {json.load(open(f))["meta"]["impl"] for f in glob.glob(out + "/*/*.json")}
metas = {json.loads(open(f).readline())["meta"]["impl"] for f in glob.glob(out + "/match-*.jsonl")}
assert impls | metas == {"cpu"}, (impls, metas)
print("engine_so_sha256", h(pokercpp_engine.__file__))
print("base_so_sha256", h(pokercpp_engine_base.__file__))
print("impl cpu")
E
if [ -e "$out/FAILED" ]; then echo "pin FAILED: $(tr '\n' ' ' <"$out/FAILED")" >&2; exit 1; fi
echo "pin ok: $out ($(find "$out" -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.txt' \) | wc -l | tr -d ' ') pinned files)"
