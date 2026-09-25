"""`ensure-monitors.py` run against a fake `ps` whose process table holds this session's monitors, another session's, or none.

Run: python3 -m unittest discover mumu-team/tests
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

# The session's name keys its mission (`team.session_key`): run as no named Claude session.
os.environ["CLAUDE_PID"] = str(os.getpid())

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"
CLAUDE, OTHER_CLAUDE = 100, 200


NOW = time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(time.time() + 60))
OLD = "Mon Jan  1 00:00:00 2001"


def row(pid, ppid, command, start=NOW):
    return f"{pid:>6} {ppid:>6} {start} {command}"


def monitor(pid, claude, name, start=NOW):
    """A monitor as the plugin runs it: a shell under Claude, and python under the shell."""
    return [row(pid, claude, f"/bin/zsh -c eval '\"/p/bin/{name}.py\" \"/d\"'", start),
            row(pid + 1, pid, f"python3 /p/bin/{name}.py /d", start)]


class EnsureMonitors(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.data = self.tmp / "config" / "plugins" / "data" / "mumu-team-x"
        (self.data / "mission").mkdir(parents=True)
        (self.data / "mission" / "s1.md").write_text("GOAL: g\n")

    def ensure(self, *rows):
        table = self.tmp / "table"
        table.write_text("\n".join([row(1, 0, "launchd"), row(CLAUDE, 1, "claude"), row(OTHER_CLAUDE, 1, "claude"), *rows]) + "\n")
        (self.tmp / "ps").write_text(f"#!/bin/sh\ncat '{table}'\n")
        (self.tmp / "ps").chmod(0o755)
        env = dict(os.environ, PATH=f"{self.tmp}:{os.environ['PATH']}", CLAUDE_PID=str(CLAUDE),
                   CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_CODE_SESSION_ID="s1")
        done = subprocess.run([sys.executable, str(BIN / "ensure-monitors.py")], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return [line.split(":")[0] for line in done.stdout.splitlines()]

    def test_none_running_names_both(self):
        self.assertEqual(self.ensure(), ["worker-watch", "lead-heartbeat"])

    def test_both_running_names_none(self):
        self.assertEqual(self.ensure(*monitor(300, CLAUDE, "worker-watch"), *monitor(400, CLAUDE, "lead-heartbeat")), [])

    def test_one_running_names_the_other(self):
        self.assertEqual(self.ensure(*monitor(300, CLAUDE, "worker-watch")), ["lead-heartbeat"])
        self.assertEqual(self.ensure(*monitor(400, CLAUDE, "lead-heartbeat")), ["worker-watch"])

    def test_another_sessions_monitors_do_not_count(self):
        self.assertEqual(self.ensure(*monitor(300, OTHER_CLAUDE, "worker-watch"), *monitor(400, OTHER_CLAUDE, "lead-heartbeat")),
                         ["worker-watch", "lead-heartbeat"])

    def test_monitor_older_than_its_code_is_named(self):
        self.assertEqual(self.ensure(*monitor(300, CLAUDE, "worker-watch", OLD), *monitor(400, CLAUDE, "lead-heartbeat")),
                         ["worker-watch"])

    def test_line_is_the_command_to_arm(self):
        self.ensure()
        env = dict(os.environ, PATH=f"{self.tmp}:{os.environ['PATH']}", CLAUDE_PID=str(CLAUDE),
                   CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_CODE_SESSION_ID="s1")
        out = subprocess.run([sys.executable, str(BIN / "ensure-monitors.py")], env=env, capture_output=True, text=True).stdout
        self.assertEqual(out.splitlines()[0], f'worker-watch: "{BIN / "worker-watch.py"}" "{self.data}"')

    def test_no_mission_fails(self):
        (self.data / "mission" / "s1.md").unlink()
        env = dict(os.environ, CLAUDE_PID=str(CLAUDE), CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_CODE_SESSION_ID="s1")
        done = subprocess.run([sys.executable, str(BIN / "ensure-monitors.py")], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)


if __name__ == "__main__":
    unittest.main()
