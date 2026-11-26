#!/bin/sh
# usage (from the repo root): sh results/2026-11-26-live-scripts/run.sh [LOG...]   (no args: the 24 Nov logs)
D=$(dirname "$0")
[ $# -eq 0 ] && set -- results/live-logs/2026-11-24_*.log
exec python3 -I "$D/analyze.py" "$@"
