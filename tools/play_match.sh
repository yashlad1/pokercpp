#!/bin/bash
# Play matches of the pokercpp bot on Chipzen's external-API lobby, one at a
# time. Each match gets its own new timestamped log, then copy the scrubbed log into results/live-logs/
# (tools/import_logs.py). Every run gets its own log; nothing is overwritten.
#
# Needs .chipzen/chipzen.toml in this repo (gitignored) with [external_api]
# token and bot_id, and the chipzen-bot SDK with the engine built for the same
# Python (tools/build_engine.sh). The SDK defaults to ~/chipzen-run/.venv;
# set CHIPZEN_SDK to use another.
#
# Usage: tools/play_match.sh [matches]     (default 1; each match gets its own log)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${CHIPZEN_SDK:-$HOME/chipzen-run/.venv/bin/chipzen-sdk}"
MATCHES="${1:-1}"
[[ $MATCHES =~ ^[1-9][0-9]*$ ]] || { echo "matches must be a positive integer" >&2; exit 1; }
LOGDIR="${CHIPZEN_LOG_DIR:-$HOME/chipzen-run/logs}"
CONF="$REPO/.chipzen"

[ -f "$CONF/chipzen.toml" ] || { echo "missing $CONF/chipzen.toml (see the header)"; exit 1; }
git -C "$REPO" check-ignore -q "$CONF/chipzen.toml" || { echo "refusing to run: $CONF/chipzen.toml is not gitignored"; exit 1; }
command -v "$SDK" >/dev/null 2>&1 || { echo "chipzen-sdk not found at $SDK: set CHIPZEN_SDK"; exit 1; }

mkdir -p "$LOGDIR"
# Run from the conf dir: the SDK finds ./chipzen.toml there, and from the repo root 'import chipzen' would find
# the repo's chipzen/ folder instead of the SDK.
cd "$CONF" || exit 1
log=
trap '[ -n "$log" ] && python3 "$REPO/tools/import_logs.py" --interrupted "$log"; exit 130' INT
CAF=""
command -v caffeinate >/dev/null 2>&1 && CAF="caffeinate -i"
for ((i = 1; i <= MATCHES; i++)); do
  POKERCPP_COMMIT="$(git -C "$REPO" rev-parse --short HEAD)"
  git -C "$REPO" diff --quiet HEAD -- chipzen/ || POKERCPP_COMMIT="$POKERCPP_COMMIT-dirty"
  export POKERCPP_COMMIT
  log="$LOGDIR/live-$(date +%Y%m%d-%H%M%S)-$i.log"
  echo "log: $log"
  PYTHONPATH="$REPO/chipzen" $CAF "$SDK" run-external "$REPO/chipzen/bot.py" \
    --max-matches 1 --log-level INFO 2>&1 | tee "$log"
  code=${PIPESTATUS[0]}
  python3 "$REPO/tools/import_logs.py" "$log"
  [ "$code" -eq 0 ] || exit "$code"
done
