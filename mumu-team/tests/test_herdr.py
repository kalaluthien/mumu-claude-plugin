"""`lib/herdr.py` against a fake `herdr` that logs every call and plays a Claude session behind a trust dialog.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
open(d / "calls", "a").write(json.dumps(a) + "\n")
if (d / "fail").exists():
    print(json.dumps({"error": {"code": (d / "fail").read_text()}}))
    sys.exit(1)
if a[:2] == ["agent", "list"]:
    ready = (d / "answered").exists()
    print(json.dumps({"result": {"agents": [{"name": "w-1-1", "pane_id": "p1", "interactive_ready": ready}]}}))
elif a[:2] == ["agent", "start"] and (d / "busy").exists():
    (d / "busy").unlink()
    print(json.dumps({"error": {"code": "agent_pane_busy"}}))
    sys.exit(1)
elif a[:2] == ["agent", "read"]:
    print("Yes, I trust this folder")
elif a[:2] == ["agent", "send-keys"]:
    (d / "answered").touch()
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "p9"}}}))
'''


class Herdr(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "herdr").write_text(FAKE)
        (self.tmp / "herdr").chmod(0o755)
        patch = mock.patch.dict(os.environ, {"PATH": f"{self.tmp}:{os.environ['PATH']}", "FAKE": str(self.tmp)})
        patch.start()
        self.addCleanup(patch.stop)

    def calls(self):
        return [json.loads(line) for line in (self.tmp / "calls").read_text().splitlines()]

    def test_agent_by_name(self):
        self.assertEqual(herdr.agent("w-1-1")["pane_id"], "p1")
        self.assertIsNone(herdr.agent("gone-1-1"))

    def test_open_tab_returns_its_pane(self):
        self.assertEqual(herdr.open_tab("/w", "w-1-1", "--no-focus"), "p9")
        self.assertEqual(self.calls(), [["tab", "create", "--cwd", "/w", "--label", "w-1-1", "--no-focus"]])

    def test_launch_retries_a_busy_pane_and_answers_the_trust_dialog(self):
        (self.tmp / "busy").touch()
        herdr.launch("w-1-1", "p1", ["--model", "opus"], 10, 0)
        calls = self.calls()
        self.assertEqual(sum(c[:2] == ["agent", "start"] for c in calls), 2)
        self.assertIn(["agent", "send-keys", "p1", "down", "enter"], calls)

    def test_launch_raises_on_another_error(self):
        (self.tmp / "fail").write_text("agent_exists")
        with self.assertRaises(RuntimeError) as e:
            herdr.launch("w-1-1", "p1", [], 10, 0)
        self.assertIn("agent_exists", str(e.exception))

    def test_unreadable_output_raises(self):
        (self.tmp / "herdr").write_text("#!/bin/sh\necho nope\n")
        self.assertRaises(RuntimeError, herdr.agents)


if __name__ == "__main__":
    unittest.main()
