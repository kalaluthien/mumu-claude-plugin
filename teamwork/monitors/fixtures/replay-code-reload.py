#!/usr/bin/env python3
"""Run a copy of the heartbeat `print-team-gaps.py` and its lib as a manager with one worker and an open task nobody holds, on a scratch repository with a git board and the fake
herdr, then change its code under it as a merge pulled into the checkout does, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`, exiting 1 on FAIL.

Cases: `start`, the task's `route` line shows; `broken`, a lib module that fails to load leaves the monitor running its old code; `lib`, that module fixed runs the new code in the
same process, which prints its gaps again; `script`, a change to the script alone does the same; `arguments`, the process running the new code still has its `--polls`; `moved`, the
script moved away, as a merge that renames it does, leaves the monitor running its old code.

usage: replay-code-reload.py"""
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
POLLS = 400  # far more than the cases take, so the monitor is still polling when the last one ends
BROKEN_SECONDS = 3  # about 10 polls, in which a monitor that loaded the broken module would end
MARK = "loaded by pid"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("code-reload-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("x-manager", 1, "working"), replay_probe.agent("t-worker", 2)])
        plugin = work / "plugin"
        (plugin / "monitors").mkdir(parents=True)
        shutil.copytree(ROOT / "lib", plugin / "lib", ignore=shutil.ignore_patterns("__pycache__"))
        for entry in ROOT.iterdir():  # the parts the copy's code reads but never changes, such as a skill's assets
            if entry.name not in ("lib", "monitors"):
                (plugin / entry.name).symlink_to(entry)
        monitor = plugin / "monitors" / "print-team-gaps.py"
        shutil.copy2(replay_probe.MONITOR, monitor)
        module = plugin / "lib" / "team_signal.py"
        original = module.read_text()
        filed = sandbox.python(USE_BOARD, "file", "--title", "Reload a task", "--body", replay_probe.write_text(work, "body.md", "Reload a task.\n"), "--label", "scope:x", pane="w1:p1")
        route = f"route #{filed.stdout.strip().rsplit('/', 1)[-1].removesuffix('.json')} "

        def monitor_pid():
            """The pid of the Python process that runs the copy with its arguments, never the stand-in `claude` above it, whose command line ends alike."""
            listing = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines()
            return next((int(line.split()[0]) for line in listing if line.split()[1:] == [sys.executable, str(monitor), "--polls", str(POLLS)]), None)

        with sandbox.monitor("w1:p1", POLLS, work / "monitor.log", monitor, TEAMWORK_MONITOR_POLL="0.3") as live:
            cases.step("start", live.until(lambda: route in live.text()), live.text())
            pid = monitor_pid()
            module.write_text(original + "\nthis line does not load(\n")
            time.sleep(BROKEN_SECONDS)
            cases.step("broken", live.process.poll() is None and monitor_pid() == pid is not None, live.text())
            routes = live.text().count(route)
            module.write_text(original + f"\nprint('{MARK}', __import__('os').getpid(), flush=True)\n")
            cases.step("lib", live.until(lambda: f"{MARK} {pid}\n" in live.text() and live.text().count(route) > routes), live.text())
            routes = live.text().count(route)
            monitor.write_text(monitor.read_text() + "\n")
            cases.step("script", live.until(lambda: live.text().count(f"{MARK} {pid}\n") == 2 and live.text().count(route) > routes), live.text())
            cases.step("arguments", monitor_pid() == pid, f"no process {pid} runs {monitor} --polls {POLLS} after the reload")
            monitor.rename(monitor.with_name("print-team-gaps-moved.py"))
            time.sleep(BROKEN_SECONDS)
            cases.step("moved", live.process.poll() is None and monitor_pid() == pid, live.text())
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
