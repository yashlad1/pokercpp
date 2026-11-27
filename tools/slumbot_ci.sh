#!/bin/bash
# Slumbot session as CI runs it (issue #186). Run from the repo root.
#   PY=python tools/slumbot_ci.sh OUT HANDS SIMS SEED
set -euo pipefail
: "${PY:?set PY to the python with pybind11, pokerkit, chipzen-bot}"
[ $# -eq 4 ] || { echo "usage: $0 OUT HANDS SIMS SEED" >&2; exit 2; }
OUT=$1 HANDS=$2 SIMS=$3 SEED=$4
for v in "$HANDS" "$SIMS" "$SEED"; do
  [[ $v =~ ^[0-9]+$ ]] || { echo "not an integer: $v" >&2; exit 2; }
done
mkdir -p "$OUT"
tools/build_engine.sh
export PYTHONPATH=chipzen
"$PY" - "$OUT/build_info.txt" <<'P'
import subprocess, sys, pokercpp_engine
info = pokercpp_engine.build_info()
open(sys.argv[1], "w").write(f"{info}\n")
print(info)
sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
sys.exit(f"engine sha {info['git_sha']} != checkout {sha}") if info["git_sha"] != sha else None
P
"$PY" tools/slumbot.py --hero bot --hands "$HANDS" --sims "$SIMS" --seed "$SEED" --log "$OUT/slumbot.jsonl" | tee "$OUT/run.txt"
"$PY" tools/slumbot_report.py "$OUT/slumbot.jsonl" > "$OUT/report.txt"
