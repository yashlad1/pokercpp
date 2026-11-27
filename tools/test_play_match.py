"""Black-box test for tools/play_match.sh: one log file per match.

Builds a throwaway git repo in a temp dir with a dummy config and a stub SDK;
the real .chipzen/ is never touched. Run: python3 tools/test_play_match.py

Not tested: Ctrl-C (SIGINT) importing the current log with --interrupted and
exiting 130; hard to trigger reliably from a test.
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
touch "$d/calls"
n=$(wc -l < "$d/calls")
echo "$*" >> "$d/calls"
echo "$POKERCPP_COMMIT $(git -C "$FIXTURE_REPO" rev-parse --short HEAD)" >> "$d/stamps"
if [ "$((n))" = 0 ] && [ -n "$COMMIT_IN_CALL1" ]; then
  echo x >> "$FIXTURE_REPO/tools/import_logs.py"
  git -C "$FIXTURE_REPO" -c user.name=t -c user.email=t@t commit -qam bump
fi
echo "2026-01-02 03:04:05,678 INFO stub start"
echo "2026-01-02 03:04:06,000 INFO match_start"
echo "2026-01-02 03:04:07,000 INFO session ended"
code=$(sed -n "$((n+1))p" "$d/codes" 2>/dev/null)
exit "${code:-0}"
"""


LAST_STAMPS = []


def run(codes, args, commit_in_call1=False):
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
        env = dict(os.environ, CHIPZEN_SDK=str(sdk), CHIPZEN_LOG_DIR=str(logs), FIXTURE_REPO=str(repo))
        if commit_in_call1:
            env["COMMIT_IN_CALL1"] = "1"
        p = subprocess.run(["bash", str(repo / "tools" / "play_match.sh"), *args],
                           env=env, capture_output=True, text=True, timeout=120)
        calls = (sdk.parent / "calls").read_text().splitlines() if (sdk.parent / "calls").exists() else []
        logfiles = sorted(x.name for x in logs.glob("*")) if logs.exists() else []
        st = sdk.parent / "stamps"
        LAST_STAMPS[:] = [l.split() for l in st.read_text().splitlines()] if st.exists() else []
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


def test_stamp_per_match():
    p, calls, _, _ = run([], ["2"], commit_in_call1=True)
    assert p.returncode == 0, p.stderr
    assert len(LAST_STAMPS) == 2, LAST_STAMPS
    (s1, h1), (s2, h2) = LAST_STAMPS
    assert s1 == h1 and s2 == h2, LAST_STAMPS
    assert s1 != s2, LAST_STAMPS


def test_rejects_bad_count():
    for bad in ("0", "abc"):
        p, calls, logs, _ = run([], [bad])
        assert p.returncode == 1, (bad, p.returncode)
        assert not calls and not logs, (bad, calls, logs)


def test_trap_empty_log_skips_import():
    """Ctrl-C before the first match starts: $log is empty, so no import call; still exit 130."""
    import signal
    import time
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        repo = t / "repo"
        (repo / "tools").mkdir(parents=True)
        (repo / "chipzen").mkdir()
        (repo / ".chipzen").mkdir()
        (repo / ".gitignore").write_text(".chipzen/\n")
        (repo / ".chipzen" / "chipzen.toml").write_text("placeholder\n")
        shutil.copy(TOOLS / "play_match.sh", repo / "tools" / "play_match.sh")
        marker = t / "imports"
        (repo / "tools" / "import_logs.py").write_text(
            f"import sys\nopen({str(marker)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        sdk = t / "sdk" / "stub"
        sdk.parent.mkdir()
        sdk.write_text("#!/bin/bash\nexit 0\n")
        sdk.chmod(0o755)
        # fake git: the first rev-parse (inside the loop, before $log is set) hangs; the rest is real git
        fake = t / "bin"
        fake.mkdir()
        (fake / "git").write_text(
            '#!/bin/bash\nif [ "$1" = -C ] && [ "$3" = rev-parse ]; then touch "$HANG"; sleep 30; fi\n'
            f'exec {shutil.which("git")} "$@"\n')
        (fake / "git").chmod(0o755)
        hang = t / "hang"
        env = dict(os.environ, CHIPZEN_SDK=str(sdk), CHIPZEN_LOG_DIR=str(t / "logs"), HANG=str(hang),
                   PATH=f"{fake}:{os.environ['PATH']}")
        p = subprocess.Popen(["bash", str(repo / "tools" / "play_match.sh"), "1"], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                             preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
        for _ in range(100):
            if hang.exists():
                break
            time.sleep(0.1)
        assert hang.exists(), "script never reached the loop"
        os.killpg(p.pid, signal.SIGINT)
        try:
            rc = p.wait(timeout=20)
        finally:
            if p.poll() is None:
                p.kill()
        assert rc == 130, rc
        assert not marker.exists(), marker.read_text()


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
