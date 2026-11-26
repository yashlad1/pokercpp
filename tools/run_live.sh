#!/bin/bash
# Keep the pokercpp bot playing: run tools/play_match.sh over and over, each
# session with its own new log, until Ctrl-C. See play_match.sh for setup.
#
# Usage: tools/run_live.sh [matches_per_session]     (default 1)
#
# Every match counts toward Chipzen's daily match limit (20 a day on the free
# plan when this was written), and with auto-accept on, the bot accepts
# challenges while this runs.
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
DELAY=30  # seconds between sessions, so a broken setup does not hammer the server
trap 'echo "stopped"; exit 0' INT TERM

while true; do
  "$DIR/play_match.sh" "$@"
  echo "$(date '+%F %T') session ended; next in ${DELAY}s (Ctrl-C to stop)"
  sleep "$DELAY"
done
