#!/usr/bin/env python3
"""Run the heartbeat `print-team-gaps.py` as a manager on a temporary repository with a git board and the fake herdr of the kick-off fixtures, over three workers at their
prompt that hold nothing open: one with a process still running under its session id, as a check it detached with `( ... ) &` does; one whose only processes under its id
are its own heartbeat and a daemon older than the limit a command left behind; and one whose session id is empty. Print `PASS` when only the first gets no `idle` line, else
`FAIL`, and exit 1 on FAIL.

usage: replay-idle-workers.py"""
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
LIMIT_SECONDS = 8
WAIT_SECONDS = 30
SETTLE_SECONDS = 3  # the monitor goes on polling, so an `idle` line wrongly printed later shows


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="idle-workers-"))
    repository, state, log = work / "repo", work / "herdr.json", work / "monitor.log"
    repository.mkdir()
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CODE_SESSION_ID"}
    environment.update(replay_probe.IDENTITY, CLAUDE_CONFIG_DIR=str(work / "claude"), GIT_CONFIG_GLOBAL=str(work / "gitconfig"), TEAMWORK_FAKE_HERDR_STATE=str(state),
                       PATH=f"{FAKE_HERDR}:{os.environ['PATH']}", HERDR_PANE_ID="w1:p1", TEAMWORK_MONITOR_POLL="0.3", TEAMWORK_BACKGROUND_SECONDS=str(LIMIT_SECONDS))
    replay_probe.write_git_config(work)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True, env=environment)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "start"], cwd=repository, check=True, env=environment)
    agents = [{"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": status, "interactive_ready": True,
               **({"agent_session": {"value": session}} if session is not None else {})}
              for name, pane, status, session in (("x-manager", 1, "working", None), ("b-busy-worker", 2, "idle", BUSY), ("b-free-worker", 3, "idle", FREE), ("b-empty-worker", 4, "idle", ""))]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))
    sleeps = [sys.executable, "-c", "import time; time.sleep(120)"]
    started = []

    def detach(session, *words):
        started.append(subprocess.Popen([*sleeps, *words], env={**environment, "CLAUDE_CODE_SESSION_ID": session}, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, start_new_session=True))

    detach(FREE)
    time.sleep(LIMIT_SECONDS + 1)  # the daemon is now older than the limit
    detach(BUSY)
    detach(FREE, str(MONITOR) + " ")  # a worker's own heartbeat
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
        for process in started:
            process.kill()
            process.wait()
    saw = log.read_text()
    quiet, idle = "idle b-busy-worker" not in saw, "idle b-free-worker" in saw and "idle b-empty-worker" in saw
    print("PASS" if quiet and idle else "FAIL")
    return 0 if quiet and idle else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
