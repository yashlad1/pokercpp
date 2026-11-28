#!/usr/bin/env python3
"""Black-box test for tools/slumbot.py exit code (issue #186).

A session that stops early (every request fails after its retries) must exit
non-zero. The proxy points at a closed local port, so nothing leaves the machine.
"""
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "slumbot.py"
PROXY = "http://127.0.0.1:9"


def port9_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 9)) == 0


class SlumbotExit(unittest.TestCase):
    def test_unreachable_server_exits_nonzero(self):
        if port9_open():
            self.skipTest("127.0.0.1:9 is open; closed-port proxy guard would not hold")
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "s.jsonl"
            env = dict(os.environ, PYTHONPATH=str(ROOT / "chipzen"),
                       https_proxy=PROXY, HTTPS_PROXY=PROXY)
            r = subprocess.run([sys.executable, str(TOOL), "--hero", "bot", "--hands", "1",
                                "--sims", "200", "--log", str(log)],
                               env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0, "exit code was 0 on an early stop\n" + r.stdout + r.stderr)
            self.assertTrue(not log.exists() or log.read_text() == "", "no hand was played, log must be empty")


if __name__ == "__main__":
    unittest.main()
