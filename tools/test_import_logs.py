#!/usr/bin/env python3
"""Black-box tests for tools/import_logs.py (--interrupted, --out)."""
import pathlib
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent / "import_logs.py"
HOME = str(pathlib.Path.home())
UUID = "123e4567-e89b-12d3-a456-426614174000"
BODY = f"2026-11-26 12:34:56 token cz_extbot_AbC123xyz id {UUID} path {HOME}/chipzen-run/x\n"
ENDED = BODY + "2026-11-26 12:40:00 session ended\n"
EXPECT_NAME = "2026-11-26_123456-{}.log"


def run_external_running():
    return subprocess.run(["pgrep", "-f", "run-external"], capture_output=True).returncode == 0


def tool(out, *args):
    r = subprocess.run([sys.executable, str(TOOL), "--out", str(out), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def written(out):
    return sorted(p.name for p in pathlib.Path(out).glob("*")) if pathlib.Path(out).exists() else []


class Dummy:
    def __enter__(self):
        self.p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "run-external"])
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


def test_refuse_when_running():
    with tempfile.TemporaryDirectory() as d, Dummy():
        out, (log,) = setup(d, a=BODY)
        rc, txt = tool(out, "--interrupted", log)
        assert rc != 0, txt
        assert any(l.startswith("refusing:") for l in txt.splitlines()), txt
        assert written(out) == []


def test_import_interrupted():
    if run_external_running():
        print("  (skipped: a real run-external process is running)")
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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(name)
            fn()
    print("ok")
