#!/usr/bin/env python3
"""Copy live match logs into results/live-logs/, scrubbed for a public repo.

Reads ~/chipzen-run/*.log and ~/chipzen-run/logs/*.log, or the paths given
as arguments. Skips a log whose session has not ended (its match may still
be running) and any log already imported unchanged. Masks API tokens, every
UUID (bot, match, round and request ids) and the home-directory path.

    python3 tools/import_logs.py [--interrupted] [--out DIR] [log ...]

--out DIR writes to DIR instead of results/live-logs/. --interrupted also imports
a log with no "session ended" line (a killed session), but only when no
run-external process is running; otherwise it refuses and writes nothing.
"""
import argparse
import pathlib
import re
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "live-logs"
HOME = str(pathlib.Path.home())
SCRUB = [
    (re.compile(r"cz_extbot_[A-Za-z0-9]+"), "cz_extbot_[REDACTED]"),
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), "[uuid]"),
    (re.compile(re.escape(HOME)), "~"),
]
STAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", re.M)


def main(paths, out=OUT, interrupted=False):
    if not paths:
        base = pathlib.Path.home() / "chipzen-run"
        paths = sorted(base.glob("*.log")) + sorted((base / "logs").glob("*.log"))
    # Ceiling: an SDK started from a path not named chipzen-sdk (via CHIPZEN_SDK) is not detected.
    if interrupted and subprocess.run(["pgrep", "-f", "chipzen-sdk run-external"], capture_output=True).returncode != 1:
        sys.exit("refusing: a run-external process is running, its log may still be growing")
    out.mkdir(parents=True, exist_ok=True)
    for p in map(pathlib.Path, paths):
        text = p.read_text(errors="replace")
        if "session ended" not in text and not interrupted:
            print(f"skip, session not ended yet: {p.name}")
            continue
        for rx, sub in SCRUB:
            text = rx.sub(sub, text)
        m = STAMP.search(text)
        stamp = m.group().replace(" ", "_").replace(":", "") if m else time.strftime(
            "%Y-%m-%d_%H%M%S", time.localtime(p.stat().st_mtime))
        dest = out / f"{stamp}-{p.stem}.log"
        if dest.exists() and dest.read_text() == text:
            print(f"already imported: {dest.name}")
            continue
        dest.write_text(text)
        print(f"imported: {dest.name} ({text.count(' -> ')} lines with '->', "
              f"{text.count('round_result hand=')} hands)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--interrupted", action="store_true")
    ap.add_argument("logs", nargs="*")
    a = ap.parse_args()
    main(a.logs, a.out, a.interrupted)
