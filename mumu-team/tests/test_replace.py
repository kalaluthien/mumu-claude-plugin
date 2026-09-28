"""`lead-start.py --replace`: a plain session starts its project's lead, and a detached child closes the session once its turn ends.

Run: python3 -m unittest discover mumu-team/tests
"""
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_literal import FORBIDDEN, fill, guard  # noqa: E402

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"
CALLER, CALLER_TAB, LEAD_PANE = "w1:p5", "w1:t14", "w1:p9"

# One fake for `herdr` and `gh`, chosen by the name it is called as; state lives in files under $REPLACE_FAKE.
# The caller is unnamed, in a tab labelled `14`, and reads `working` until the file `turn-ended` exists.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, tool, a = pathlib.Path(os.environ["REPLACE_FAKE"]), pathlib.Path(sys.argv[0]).name, sys.argv[1:]
def log(*call):
    with open(d / "calls", "a") as f:
        f.write(json.dumps({"sid": os.getsid(0), "call": list(call)}) + "\n")
log(tool, *a)
alive, screen = d / "alive", d / "screen"
if tool == "gh":
    print("main")
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "%s"}}}))
elif a[:2] == ["tab", "list"]:
    print(json.dumps({"result": {"tabs": [{"label": "14", "tab_id": "%s"}, {"label": "main-lead", "tab_id": "w1:t9"}]}}))
elif a[:2] == ["agent", "start"]:
    (d / "lead").write_text(a[2])
    print(json.dumps({"result": {}}))
elif a[:2] == ["agent", "list"]:
    agents = [{"name": (d / "lead").read_text(), "pane_id": "%s", "tab_id": "w1:t9", "agent_status": "idle", "interactive_ready": True}] if (d / "lead").exists() else []
    if alive.exists():
        status = "idle" if (d / "turn-ended").exists() else "working"
        log("served", status)
        agents.append({"pane_id": "%s", "tab_id": "%s", "agent_status": status, "interactive_ready": True})
    print(json.dumps({"result": {"agents": agents}}))
elif a[:2] == ["agent", "prompt"] and a[2:] == ["%s", "/exit"]:
    screen.write_text("Background work is running\n ❯ 1. Exit\n   2. Keep running")
elif a[:2] == ["agent", "read"]:
    print(screen.read_text() if screen.exists() else "❯")
elif a[:2] == ["agent", "send-keys"] and a[2:] == ["%s", "enter"] and screen.exists():
    screen.unlink()
    alive.unlink()
''' % (LEAD_PANE, CALLER_TAB, LEAD_PANE, CALLER, CALLER_TAB, CALLER, CALLER)


class Replace(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.tmp / "alive").touch()
        for tool in ("herdr", "gh"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)
        self.env = dict(os.environ, REPLACE_FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}", HERDR_PANE_ID=CALLER,
                        LEAD_START_TIMEOUT="3", LEAD_START_POLL="0.01", WORKER_CLOSE_POLL="0.02", WORKER_CLOSE_TIMEOUT="5",
                        WORKER_CLOSE_IDLE_TIMEOUT="20", CLAUDE_PID="")

    def start(self, *extra, env=None):
        return subprocess.run([sys.executable, str(BIN / "lead-start.py"), str(self.repo), *extra], env=env or self.env,
                              capture_output=True, text=True, timeout=30)

    def calls(self):
        log = self.tmp / "calls"
        return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def wait_for(self, call, seconds=15):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if any(c["call"] == call for c in self.calls()):
                return self.calls()
            time.sleep(0.05)
        self.fail(f"never called: {call}; calls: {[c['call'] for c in self.calls()]}")

    def replace(self):
        done = self.start("--replace")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, f"main-lead@{LEAD_PANE}\n")
        time.sleep(0.3)  # the caller's turn goes on for several polls after the call returns
        returned = self.calls()
        (self.tmp / "turn-ended").touch()
        return returned, self.wait_for(["herdr", "tab", "close", CALLER_TAB])

    def test_lead_live_before_the_caller_is_touched(self):
        returned, calls = self.replace()
        order = [c["call"] for c in calls]
        kickoff = order.index(["herdr", "agent", "prompt", LEAD_PANE, "/mumu-team:kickoff"])
        self.assertLess(order.index(["herdr", "agent", "start", "main-lead", "--kind", "claude", "--pane", LEAD_PANE, "--",
                                     "--name", "main-lead", "--agent", "mumu-team:lead", "--model", "opus", "--effort", "medium"]), kickoff)
        touched = [i for i, c in enumerate(order) if CALLER in c]
        self.assertTrue(touched)
        self.assertLess(kickoff, touched[0], "the caller was reached before its lead was live")
        self.assertFalse([c for c in returned if CALLER in c["call"]], "the caller was reached during its own turn")

    def test_exit_only_after_the_caller_reads_idle(self):
        _, calls = self.replace()
        order = [c["call"] for c in calls]
        exit_ = order.index(["herdr", "agent", "prompt", CALLER, "/exit"])
        served = [c[1] for c in order[:exit_] if c[0] == "served"]
        self.assertGreaterEqual(served.count("working"), 3, "the caller never read working for several polls")
        self.assertEqual(served[-1], "idle", "/exit sent while the caller read working")

    def test_exit_dialog_answered_and_tab_closed_by_id(self):
        _, calls = self.replace()
        order = [c["call"] for c in calls]
        self.assertEqual([c for c in order if c[:3] == ["herdr", "agent", "send-keys"]], [["herdr", "agent", "send-keys", CALLER, "enter"]])
        self.assertEqual([c for c in order if c[:3] == ["herdr", "tab", "close"]], [["herdr", "tab", "close", CALLER_TAB]])
        self.assertFalse((self.tmp / "alive").exists(), "the caller left running")

    def test_close_runs_in_a_new_session_that_outlives_the_call(self):
        returned, calls = self.replace()
        mine = os.getsid(0)
        starter = {c["sid"] for c in calls if c["call"][:3] in (["herdr", "tab", "create"], ["herdr", "agent", "start"]) or LEAD_PANE in c["call"][3:4]}
        self.assertEqual(starter, {mine})
        closer = {c["sid"] for c in calls if CALLER in c["call"] and c["call"][0] == "herdr"}
        self.assertEqual(len(closer), 1, closer)
        self.assertNotEqual(closer, {mine}, "the close ran in lead-start.py's own session")
        self.assertNotIn(["herdr", "agent", "prompt", CALLER, "/exit"], [c["call"] for c in returned])

    def test_replace_refuses_a_task_url_or_succeed_and_needs_herdr(self):
        env = dict(self.env)
        del env["HERDR_PANE_ID"]
        for extra, e in ((["--replace", "https://github.com/o/main/issues/9"], None), (["--replace", "--succeed", "w1:p2"], None), (["--replace"], env)):
            done = self.start(*extra, env=e)
            self.assertEqual(done.returncode, 2, extra)
            self.assertFalse(self.calls(), extra)


class ExitSelf(unittest.TestCase):
    """`worker-close.py --self`: an idle lead exits its own session once its turn ends, from a detached child."""
    setUp, calls, wait_for = Replace.setUp, Replace.calls, Replace.wait_for

    def test_self_exits_the_caller_after_its_turn_and_closes_its_tab(self):
        done = subprocess.run([sys.executable, str(BIN / "worker-close.py"), "--self"], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        time.sleep(0.3)
        self.assertNotIn(["herdr", "agent", "prompt", CALLER, "/exit"], [c["call"] for c in self.calls()], "exit sent during the turn")
        (self.tmp / "turn-ended").touch()
        calls = self.wait_for(["herdr", "tab", "close", CALLER_TAB])
        self.assertNotEqual({c["sid"] for c in calls}, {os.getsid(0)}, "the close ran in the caller's own session")
        self.assertFalse((self.tmp / "alive").exists(), "the caller left running")

    def test_self_needs_herdr(self):
        env = dict(self.env)
        del env["HERDR_PANE_ID"]
        done = subprocess.run([sys.executable, str(BIN / "worker-close.py"), "--self"], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 2)
        self.assertFalse(self.calls())


class HandoffStep(unittest.TestCase):
    """handoff's step for the owner asking a plain session to become the lead: one literal `lead-start.py --replace` call."""

    def step(self):
        text = (BIN.parent / "skills" / "handoff" / "SKILL.md").read_text()
        steps = [s for s in re.findall(r"^\d+\. .*$", text, re.M) if "--replace" in s]
        self.assertEqual(len(steps), 1, steps)
        return text, steps[0]

    def test_the_step_is_one_literal_call_the_owner_allows(self):
        text, step = self.step()
        self.assertIn("lead로 승격", text.split("---")[1], "the description does not name the promotion")
        self.assertIn("lead로 승격", step)
        commands = [c for c in re.findall(r"`(lead-start\.py [^`]+)`", step) if "--replace" in c]
        self.assertEqual(commands, ["lead-start.py <checkout> --replace"])
        self.assertIn("--folder <folder>", step)
        self.assertRegex(step, r"`prompt` the lead this session's context")
        for command in (fill(commands[0]), fill(commands[0]) + " --folder mumu-team"):
            with self.subTest(command=command):
                self.assertNotRegex(command, FORBIDDEN)
                self.assertTrue(fnmatch.fnmatchcase(command, "lead-start.py *"))
                result = guard(command)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
