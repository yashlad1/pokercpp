#!/bin/bash
# Keep the pokercpp bot connected to Chipzen's external-API lobby, and restart
# it whenever a session ends or crashes. Ctrl-C stops it.
#
# Needs:
#   - .chipzen/chipzen.toml in this repo (gitignored) with [external_api]
#     token and bot_id. Never commit that file or paste the token anywhere.
#   - the chipzen-bot SDK, and the engine built for the same Python
#     (tools/build_engine.sh).
#
# Usage:
#   CHIPZEN_SDK=/path/to/venv/bin/chipzen-sdk tools/run_live.sh [matches_per_session]
#
# With no argument each session plays until the lobby closes, then restarts.
# Every match counts toward Chipzen's daily match limit (20 a day on the free
# plan when this was written), and with auto-accept on, the bot accepts
# challenges while this runs.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${CHIPZEN_SDK:-chipzen-sdk}"
MAX="${1:-}"
LOGDIR="${CHIPZEN_LOG_DIR:-$HOME/chipzen-run/logs}"
DELAY=30  # seconds between restarts, so a broken setup doesn't hammer the server

CONF="$REPO/.chipzen"
[ -f "$CONF/chipzen.toml" ] || { echo "missing $CONF/chipzen.toml (see the header)"; exit 1; }
git -C "$REPO" check-ignore -q "$CONF/chipzen.toml" || { echo "refusing to run: $CONF/chipzen.toml is not gitignored"; exit 1; }
command -v "$SDK" >/dev/null 2>&1 || { echo "chipzen-sdk not found: set CHIPZEN_SDK"; exit 1; }

mkdir -p "$LOGDIR"
# Run from .chipzen/: the SDK finds ./chipzen.toml there, and it is not the
# repo root, where 'import chipzen' would find the repo's chipzen/ folder
# instead of the SDK.
cd "$CONF" || exit 1
trap 'echo "stopped"; exit 0' INT TERM

while true; do
  log="$LOGDIR/live-$(date +%Y%m%d-%H%M%S).log"
  echo "$(date '+%F %T') starting a session; log: $log"
  args=(run-external "$REPO/chipzen/bot.py" --log-level INFO)
  [ -n "$MAX" ] && args+=(--max-matches "$MAX")
  PYTHONPATH="$REPO/chipzen" caffeinate -i "$SDK" "${args[@]}" 2>&1 | tee "$log"
  code=${PIPESTATUS[0]}
  echo "$(date '+%F %T') session ended (exit $code); restarting in ${DELAY}s (Ctrl-C to stop)"
  sleep "$DELAY"
done
