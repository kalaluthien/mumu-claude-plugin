#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py` as a manager on a temporary repository with a git board and the fake herdr of the kick-off fixtures, over two workers at their
prompt that hold nothing open, one with a process still running under its session id, as a check it detached with `( ... ) &` does, and one with none. Print `PASS` when
only the worker with nothing running gets an `idle` line, else `FAIL`, and exit 1 on FAIL.

usage: replay-idle-workers.py [--verbose]
`--verbose` also prints what the heartbeat printed."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

FAKE_HERDR = ROOT / "skills" / "kick-off" / "fixtures" / "fake-herdr"
MONITOR = ROOT / "monitors" / "print-team-gaps.py"
BUSY, FREE = "sess-busy", "sess-free"
WAIT_SECONDS = 30
SETTLE_SECONDS = 3  # the monitor goes on polling, so an `idle` line wrongly printed later shows


def main(args):
    if args not in ([], ["--verbose"]):
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="idle-workers-"))
    repository, state, log = work / "repo", work / "herdr.json", work / "monitor.log"
    repository.mkdir()
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CODE_SESSION_ID"}
    environment.update(replay_probe.IDENTITY, CLAUDE_CONFIG_DIR=str(work / "claude"), GIT_CONFIG_GLOBAL=str(work / "gitconfig"), TEAMWORK_FAKE_HERDR_STATE=str(state),
                       PATH=f"{FAKE_HERDR}:{os.environ['PATH']}", HERDR_PANE_ID="w1:p1", TEAMWORK_MONITOR_POLL="0.3")
    replay_probe.write_git_config(work)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True, env=environment)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "start"], cwd=repository, check=True, env=environment)
    agents = [{"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status, "interactive_ready": True,
               **({"agent_session": {"value": session}} if session else {})}
              for name, pane, status, session in (("x-manager", 1, "working", None), ("b-busy-worker", 2, "idle", BUSY), ("b-free-worker", 3, "idle", FREE))]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))
    detached = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], env={**environment, "CLAUDE_CODE_SESSION_ID": BUSY}, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        with log.open("w") as stream:
            live = replay_probe.start_as_pane([MONITOR], "w1:p1", environment, work / "stand-in", repository, stream)
            deadline = time.time() + WAIT_SECONDS
            while time.time() < deadline and "idle b-free-worker" not in log.read_text():
                time.sleep(0.2)
            time.sleep(SETTLE_SECONDS)
            live.kill()
            live.wait()
    finally:
        detached.kill()
        detached.wait()
    saw = log.read_text()
    quiet, idle = "idle b-busy-worker" not in saw, "idle b-free-worker" in saw
    if args:
        print(saw)
    print("PASS" if quiet and idle else "FAIL")
    return 0 if quiet and idle else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
