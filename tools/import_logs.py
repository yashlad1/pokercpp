#!/usr/bin/env python3
"""Copy live match logs into results/live-logs/, scrubbed for a public repo.

Reads ~/chipzen-run/*.log and ~/chipzen-run/logs/*.log, or the paths given
as arguments. Skips a log whose session has not ended (its match may still
be running) and any log already imported unchanged. Masks API tokens, every
UUID (bot, match, round and request ids) and the home-directory path.

    python3 tools/import_logs.py [log ...]
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "live-logs"
HOME = str(pathlib.Path.home())
SCRUB = [
    (re.compile(r"cz_extbot_[A-Za-z0-9]+"), "cz_extbot_[REDACTED]"),
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), "[uuid]"),
    (re.compile(re.escape(HOME)), "~"),
]


def main(paths):
    if not paths:
        base = pathlib.Path.home() / "chipzen-run"
        paths = sorted(base.glob("*.log")) + sorted((base / "logs").glob("*.log"))
    OUT.mkdir(parents=True, exist_ok=True)
    for p in map(pathlib.Path, paths):
        text = p.read_text(errors="replace")
        if "session ended" not in text:
            print(f"skip, session not ended yet: {p.name}")
            continue
        for rx, sub in SCRUB:
            text = rx.sub(sub, text)
        stamp = text[:19].replace(" ", "_").replace(":", "")
        dest = OUT / f"{stamp}-{p.stem}.log"
        if dest.exists() and dest.read_text() == text:
            print(f"already imported: {dest.name}")
            continue
        dest.write_text(text)
        print(f"imported: {dest.name} ({text.count(' -> ')} lines with '->', "
              f"{text.count('round_result hand=')} hands)")


if __name__ == "__main__":
    main(sys.argv[1:])
