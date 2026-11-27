#!/usr/bin/env python3
"""Black-box tests for tools/import_logs.py (--interrupted, --out)."""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

TOOL = pathlib.Path(__file__).resolve().parent / "import_logs.py"
HOME = str(pathlib.Path.home())
UUID = "123e4567-e89b-12d3-a456-426614174000"
BODY = f"2026-11-26 12:34:56 token cz_extbot_AbC123xyz id {UUID} path {HOME}/chipzen-run/x\n"
ENDED = BODY + "2026-11-26 12:40:00 session ended\n"
EXPECT_NAME = "2026-11-26_123456-{}.log"

SUB = "run-" + "external"  # built by concatenation: the real guard matches this text


def run_external_running():
    return subprocess.run(["pgrep", "-f", SUB], capture_output=True).returncode == 0


def tool(out, *args):
    r = subprocess.run([sys.executable, str(TOOL), "--out", str(out), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def written(out):
    return sorted(p.name for p in pathlib.Path(out).glob("*")) if pathlib.Path(out).exists() else []


class Dummy:
    def __enter__(self):
        self.p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "chipzen-sdk", SUB])
        return self

    def __exit__(self, *a):
        self.p.kill()
        self.p.wait()


def setup(d, **logs):
    d = pathlib.Path(d)
    paths = []
    for name, text in logs.items():
        p = d / f"{name}.log"
        p.write_text(text)
        paths.append(str(p))
    return d / "out", paths


def test_skip_without_flag():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a=BODY)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        assert "skip, session not ended yet: a.log" in txt, txt
        assert written(out) == []


def test_import_interrupted():
    if run_external_running():
        print("  (skipped: a real " + SUB + " process is running)")
        return
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a=BODY)
        rc, txt = tool(out, "--interrupted", log)
        assert rc == 0, txt
        assert written(out) == [EXPECT_NAME.format("a")], written(out)
        got = (out / EXPECT_NAME.format("a")).read_text()
        assert "cz_extbot_[REDACTED]" in got and "AbC123xyz" not in got
        assert "[uuid]" in got and UUID not in got
        assert HOME not in got and "~/chipzen-run/x" in got


def test_completed_without_flag():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a=ENDED)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        assert written(out) == [EXPECT_NAME.format("a")]


def test_reimport():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a=ENDED)
        tool(out, log)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        assert "already imported: " + EXPECT_NAME.format("a") in txt, txt


def test_mix_refused_whole_call():
    with tempfile.TemporaryDirectory() as d, Dummy():
        out, paths = setup(d, done=ENDED, cut=BODY)
        rc, txt = tool(out, "--interrupted", *paths)
        assert rc != 0, txt
        assert "refusing:" in txt, txt
        assert written(out) == []

STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}-a\.log$")
TS_LINES = "2026-11-26 21:50:25 hello\n2026-11-26 21:55:00 session ended\n"


def inside_out(out):
    return [p for p in pathlib.Path(out).iterdir() if p.is_file()] and \
        [p for p in pathlib.Path(out).rglob("*")] == list(pathlib.Path(out).iterdir())


def test_warning_first_line():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a="Warning: something /some/path\n" + TS_LINES)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        assert written(out) == ["2026-11-26_215025-a.log"], written(out)
        assert inside_out(out)


def test_path_in_first_line():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a="/tmp/x/y: No such file\n" + TS_LINES)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        names = written(out)
        assert len(names) == 1 and STAMP_RE.match(names[0]), names
        assert inside_out(out)


def test_no_timestamp_uses_mtime():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a="no stamp here\nsession ended\n")
        t = 1700000000
        os.utime(log, (t, t))
        rc, txt = tool(out, log)
        assert rc == 0, txt
        want = time.strftime("%Y-%m-%d_%H%M%S", time.localtime(t)) + "-a.log"
        assert written(out) == [want], (written(out), want)
        assert inside_out(out)


def test_normal_log_name_unchanged():
    with tempfile.TemporaryDirectory() as d:
        out, (log,) = setup(d, a=TS_LINES)
        rc, txt = tool(out, log)
        assert rc == 0, txt
        assert written(out) == ["2026-11-26_215025-a.log"], written(out)


class SleepProc:
    """A short-lived dummy whose command line holds the given words."""

    def __init__(self, *words):
        self.words = words

    def __enter__(self):
        self.p = subprocess.Popen(["sh", "-c", "sleep 60; true", *self.words])
        time.sleep(0.3)
        return self

    def __exit__(self, *a):
        self.p.kill()
        self.p.wait()


def test_bare_subcommand_text_does_not_block():
    with tempfile.TemporaryDirectory() as d, SleepProc(SUB):
        out, (log,) = setup(d, a=BODY)
        rc, txt = tool(out, "--interrupted", log)
        assert rc == 0, txt
        assert written(out) == [EXPECT_NAME.format("a")], written(out)


def test_sdk_command_line_blocks():
    with tempfile.TemporaryDirectory() as d, SleepProc("/x/bin/chipzen-sdk", SUB, "bot.py"):
        out, (log,) = setup(d, a=BODY)
        rc, txt = tool(out, "--interrupted", log)
        assert rc != 0, txt
        assert any(l.startswith("refusing:") for l in txt.splitlines()), txt
        assert written(out) == []


def test_pgrep_error_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        bindir = pathlib.Path(d) / "bin"
        bindir.mkdir()
        (bindir / "pgrep").write_text("#!/bin/sh\nexit 2\n")
        (bindir / "pgrep").chmod(0o755)
        out, (log,) = setup(d, a=BODY)
        r = subprocess.run([sys.executable, str(TOOL), "--out", str(out), "--interrupted", log],
                           capture_output=True, text=True,
                           env=dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}"))
        assert r.returncode != 0, r.stdout + r.stderr
        assert written(out) == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(name)
            fn()
    print("ok")
