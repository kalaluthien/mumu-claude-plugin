#!/usr/bin/env python3
"""Replay a held task changing under a live worker, on a temporary repository with a git board and the fake herdr beside this file, with the real heartbeat monitor running as that worker, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Cases: `start`, a task the worker already holds prints no `changed` line; `decision`, a manager's `DECIDED:` on it prints one, which names `holders`; `second`, a decision in the poll after a printed one prints its own line; `report`, the worker's own `REPORTED:`, posted after a quiet gap, prints none; and `lost`, a `holders` change to another session prints a `changed` line and then `holds nothing`.

usage: replay-worker-change.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
MONITOR = ROOT / "monitors" / "print-team-gaps.py"
SECONDS = 30
QUIET_SECONDS = 3  # about 10 polls, in which a monitor that wrongly printed would show


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="worker-change-"))
    repository, state, log = work / "repo", work / "herdr.json", work / "monitor.log"
    environment = {**os.environ, **replay_probe.IDENTITY, "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig"),
                   "TEAMWORK_FAKE_HERDR_STATE": str(state), "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_MONITOR_POLL": "0.3"}
    replay_probe.write_git_config(work)
    repository.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "start"]):
        subprocess.run(["git", *argv], cwd=repository, check=True, env=environment, capture_output=True)
    agents = [{"name": name, "pane_id": f"w1:p{pane}", "tab_id": f"w1:t{pane}", "workspace_id": "w1", "agent": "claude", "agent_status": "working", "interactive_ready": True}
              for name, pane in (("c-manager", 1), ("c-worker", 2))]
    state.write_text(json.dumps({"n": 20, "agents": agents, "tabs": [{"tab_id": each["tab_id"], "workspace_id": "w1", "label": each["name"]} for each in agents]}))

    def use(pane, *argv):
        done = subprocess.run([str(USE_BOARD), *argv], cwd=repository, env={**environment, "HERDR_PANE_ID": pane}, capture_output=True, text=True)
        return done.stdout.strip()

    def post(pane, verb, number, body):
        use(pane, verb, number, str(replay_probe.write_text(work, "post.md", body)))

    def changes():
        return log.read_text().count(f"changed #{number} ")

    def wait_for(count):
        deadline = time.time() + SECONDS
        while time.time() < deadline and changes() < count:
            time.sleep(0.2)
        return changes() >= count

    def wait_until(words):
        deadline = time.time() + SECONDS
        while time.time() < deadline and words not in log.read_text():
            time.sleep(0.2)
        return words in log.read_text()

    number = use("w1:p1", "file", "Change a held task", str(replay_probe.write_text(work, "body.md", "Change a held task.\n")), "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    post("w1:p1", "decide", number, "DECIDED: c-worker holds this.\n\n```teamwork\nholders: c-worker\n```\n")
    live = subprocess.Popen([sys.executable, str(MONITOR)], cwd=repository, env={**environment, "HERDR_PANE_ID": "w1:p2"}, stdout=log.open("w"), stderr=subprocess.STDOUT)
    cases = {}
    try:
        time.sleep(QUIET_SECONDS)
        cases["start"] = (changes() == 0, log.read_text())
        post("w1:p1", "decide", number, "DECIDED: use the other way.\n\n```decision\ndecision: use the other way\ndecided by: c-manager\ndoor: two-way\n```\n")
        cases["decision"] = (wait_for(1) and "`holders`" in log.read_text(), log.read_text())
        post("w1:p1", "decide", number, "DECIDED: and keep the old name.\n\n```decision\ndecision: keep the old name\ndecided by: c-manager\ndoor: two-way\n```\n")
        cases["second"] = (wait_for(2), log.read_text())  # a change in the poll after a printed one is its own line
        time.sleep(QUIET_SECONDS)
        post("w1:p2", "comment", number, "REPORTED: criteria at 0123abc\n")
        time.sleep(QUIET_SECONDS)
        cases["report"] = (changes() == 2, log.read_text())
        post("w1:p1", "decide", number, "DECIDED: c-other holds this.\n\n```teamwork\nholders: c-other\n```\n")
        cases["lost"] = (wait_for(3) and wait_until("holds nothing"), log.read_text())  # the task is open and names another session
    finally:
        live.kill()
        live.wait()
    for name, (passed, saw) in cases.items():
        print(f"ok {name}" if passed else f"fail {name}: {saw.strip()}", flush=True)
    ok = all(passed for passed, _ in cases.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
