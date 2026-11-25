#!/usr/bin/env python3
"""Run a copy of the heartbeat `print-team-gaps.py` and its lib as a manager with one worker and an open task nobody holds, on a temporary repository with a git board and the fake
herdr of the kick-off fixtures, then change its code under it as a merge pulled into the checkout does, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS`
or `FAIL`, exiting 1 on FAIL.

Cases: `start`, the task's `route` line shows; `broken`, a lib module that fails to load leaves the monitor running its old code; `lib`, that module fixed runs the new code in the
same process, which prints its gaps again; `script`, a change to the script alone does the same; `moved`, the script moved away, as a merge that renames it does, leaves the
monitor running its old code.

usage: replay-code-reload.py"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

FAKE_HERDR = ROOT / "skills" / "kick-off" / "fixtures" / "fake-herdr"
WAIT_SECONDS = 30
BROKEN_SECONDS = 3  # about 10 polls, in which a monitor that loaded the broken module would end
MARK = "loaded by pid"


def agent(name, pane, status="idle"):
    return {"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status, "interactive_ready": True}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="code-reload-")).resolve()  # the path the monitor runs again by, so `ps` lists one command before and after
    plugin, repository, state, log = work / "plugin", work / "repo", work / "herdr.json", work / "monitor.log"
    (plugin / "monitors").mkdir(parents=True)
    shutil.copytree(ROOT / "lib", plugin / "lib", ignore=shutil.ignore_patterns("__pycache__"))
    for entry in ROOT.iterdir():  # the parts the copy's code reads but never changes, such as a skill's assets
        if entry.name not in ("lib", "monitors"):
            (plugin / entry.name).symlink_to(entry)
    monitor = plugin / "monitors" / "print-team-gaps.py"
    shutil.copy2(ROOT / "monitors" / "print-team-gaps.py", monitor)
    module = plugin / "lib" / "team_signal.py"
    original = module.read_text()
    repository.mkdir()
    environment = {**os.environ, **replay_probe.IDENTITY, "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "PATH": f"{FAKE_HERDR}:{os.environ['PATH']}", "HERDR_PANE_ID": "w1:p1", "TEAMWORK_MONITOR_POLL": "0.3"}
    replay_probe.write_git_config(work)
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True, env=environment, capture_output=True)
    agents = [agent("x-manager", 1, "working"), agent("t-worker", 2)]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))
    body = replay_probe.write_text(work, "body.md", "Reload a task.\n")
    filed = subprocess.run([str(ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"), "file", "--title", "Reload a task", "--body", str(body), "--label", "scope:x"],
                           cwd=repository, env=environment, capture_output=True, text=True)
    route = f"route #{filed.stdout.strip().rsplit('/', 1)[-1].removesuffix('.json')} "

    def wait_until(done, seconds=WAIT_SECONDS):
        deadline = time.time() + seconds
        while time.time() < deadline and not done():
            time.sleep(0.2)
        return done()

    def monitor_pid():
        """The pid of the Python process that runs the copy, never the stand-in `claude` above it, whose command line ends alike."""
        listing = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines()
        return next((int(line.split()[0]) for line in listing if line.split()[1:] == [sys.executable, str(monitor)]), None)

    cases = {}
    live = replay_probe.start_as_pane([sys.executable, monitor], "w1:p1", environment, work / "stand-in", repository, log.open("w"))
    try:
        cases["start"] = wait_until(lambda: route in log.read_text())
        pid = monitor_pid()
        module.write_text(original + "\nthis line does not load(\n")
        time.sleep(BROKEN_SECONDS)
        cases["broken"] = live.poll() is None and monitor_pid() == pid is not None
        routes = log.read_text().count(route)
        module.write_text(original + f"\nprint('{MARK}', __import__('os').getpid(), flush=True)\n")
        cases["lib"] = wait_until(lambda: f"{MARK} {pid}\n" in log.read_text() and log.read_text().count(route) > routes) and live.poll() is None
        routes = log.read_text().count(route)
        monitor.write_text(monitor.read_text() + "\n")
        cases["script"] = wait_until(lambda: log.read_text().count(f"{MARK} {pid}\n") == 2 and log.read_text().count(route) > routes) and live.poll() is None
        monitor.rename(monitor.with_name("print-team-gaps-moved.py"))
        time.sleep(BROKEN_SECONDS)
        cases["moved"] = live.poll() is None and monitor_pid() == pid
    finally:
        live.kill()
        live.wait()
    saw = log.read_text().strip()[-1500:]
    for name, passed in cases.items():
        print(f"ok {name}" if passed else f"fail {name}: {saw}", flush=True)
    ok = all(cases.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
