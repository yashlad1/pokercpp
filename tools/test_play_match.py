"""Black-box test for tools/play_match.sh: one log file per match.

Builds a throwaway git repo in a temp dir with a dummy config and a stub SDK;
the real .chipzen/ is never touched. Run: python3 tools/test_play_match.py
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = pathlib.Path(__file__).resolve().parent

STUB = """#!/bin/bash
d="$(dirname "$0")"
n=$(wc -l < "$d/calls" 2>/dev/null || echo 0)
echo "$*" >> "$d/calls"
echo "2026-01-02 03:04:05,678 INFO stub start"
echo "2026-01-02 03:04:06,000 INFO match_start"
echo "2026-01-02 03:04:07,000 INFO session ended"
code=$(sed -n "$((n+1))p" "$d/codes" 2>/dev/null)
exit "${code:-0}"
"""


def run(codes, args):
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        repo = t / "repo"
        (repo / "tools").mkdir(parents=True)
        (repo / "chipzen").mkdir()
        (repo / ".chipzen").mkdir()
        (repo / ".gitignore").write_text(".chipzen/\n")
        (repo / ".chipzen" / "chipzen.toml").write_text("placeholder\n")
        (repo / "chipzen" / "bot.py").write_text("")
        for f in ("play_match.sh", "import_logs.py"):
            shutil.copy(TOOLS / f, repo / "tools" / f)
        g = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-qm", "init"], check=True)
        sdk = t / "sdk" / "stub"
        sdk.parent.mkdir()
        sdk.write_text(STUB)
        sdk.chmod(0o755)
        (sdk.parent / "codes").write_text("".join(f"{c}\n" for c in codes))
        logs = t / "logs"
        env = dict(os.environ, CHIPZEN_SDK=str(sdk), CHIPZEN_LOG_DIR=str(logs))
        p = subprocess.run(["bash", str(repo / "tools" / "play_match.sh"), *args],
                           env=env, capture_output=True, text=True, timeout=120)
        calls = (sdk.parent / "calls").read_text().splitlines() if (sdk.parent / "calls").exists() else []
        logfiles = sorted(x.name for x in logs.glob("*")) if logs.exists() else []
        imported = list((repo / "results" / "live-logs").glob("*.log"))
        return p, calls, logfiles, imported


def test_three_matches():
    p, calls, logs, imported = run([], ["3"])
    assert p.returncode == 0, p.stderr
    assert len(logs) == 3, logs
    assert len(calls) == 3, calls
    assert all("--max-matches 1" in c for c in calls), calls
    assert len(imported) == 3, imported


def test_stops_on_failure():
    p, calls, logs, _ = run([0, 7], ["3"])
    assert p.returncode == 7, p.returncode
    assert len(logs) == 2, logs
    assert len(calls) == 2, calls


def test_default_one():
    p, calls, logs, _ = run([], [])
    assert p.returncode == 0, p.stderr
    assert len(logs) == 1 and len(calls) == 1, (logs, calls)


def test_names_unique_and_formatted():
    _, _, logs, _ = run([], ["3"])
    assert len(set(logs)) == len(logs) == 3, logs
    assert all(re.fullmatch(r"live-\d{8}-\d{6}-\d+\.log", n) for n in logs), logs


if __name__ == "__main__":
    if not (shutil.which("git") and shutil.which("bash")):
        print("skip: git or bash missing")
        sys.exit(0)
    bad = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                bad += 1
                print("FAIL", name, "-", str(e)[:200])
    sys.exit(1 if bad else 0)
