#!/bin/bash
# Play one session of the pokercpp bot on Chipzen's external-API lobby, log it
# to a new timestamped file, then copy the scrubbed log into results/live-logs/
# (tools/import_logs.py). Every run gets its own log; nothing is overwritten.
#
# Needs .chipzen/chipzen.toml in this repo (gitignored) with [external_api]
# token and bot_id, and the chipzen-bot SDK with the engine built for the same
# Python (tools/build_engine.sh). The SDK defaults to ~/chipzen-run/.venv;
# set CHIPZEN_SDK to use another.
#
# Usage: tools/play_match.sh [matches]     (default 1)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${CHIPZEN_SDK:-$HOME/chipzen-run/.venv/bin/chipzen-sdk}"
MATCHES="${1:-1}"
LOGDIR="${CHIPZEN_LOG_DIR:-$HOME/chipzen-run/logs}"
CONF="$REPO/.chipzen"

[ -f "$CONF/chipzen.toml" ] || { echo "missing $CONF/chipzen.toml (see the header)"; exit 1; }
git -C "$REPO" check-ignore -q "$CONF/chipzen.toml" || { echo "refusing to run: $CONF/chipzen.toml is not gitignored"; exit 1; }
command -v "$SDK" >/dev/null 2>&1 || { echo "chipzen-sdk not found at $SDK: set CHIPZEN_SDK"; exit 1; }

mkdir -p "$LOGDIR"
POKERCPP_COMMIT="$(git -C "$REPO" rev-parse --short HEAD)"
git -C "$REPO" diff --quiet HEAD -- chipzen/ || POKERCPP_COMMIT="$POKERCPP_COMMIT-dirty"
export POKERCPP_COMMIT
log="$LOGDIR/live-$(date +%Y%m%d-%H%M%S).log"
echo "log: $log"
# Run from .chipzen/: the SDK finds ./chipzen.toml there, and it is not the
# repo root, where 'import chipzen' would find the repo's chipzen/ folder
# instead of the SDK.
cd "$CONF" || exit 1
PYTHONPATH="$REPO/chipzen" caffeinate -i "$SDK" run-external "$REPO/chipzen/bot.py" \
  --max-matches "$MATCHES" --log-level INFO 2>&1 | tee "$log"
code=${PIPESTATUS[0]}
python3 "$REPO/tools/import_logs.py" "$log"
exit "$code"
