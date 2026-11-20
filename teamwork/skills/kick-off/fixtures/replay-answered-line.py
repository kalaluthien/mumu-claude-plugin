#!/usr/bin/env python3
"""Replay a held task whose question a manager answered, on a temporary repository with a git board and the fake herdr beside this file, with the real heartbeat monitor started as that worker, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Cases: `unacted`, a start with the answer the worker has not acted on prints one `answered` line; and `acted`, a start after the worker's own `REPORTED:` comment on the task prints none.

usage: replay-answered-line.py"""
import json
import os
import pathlib
import signal
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
QUIET_SECONDS = 3  # about 10 polls, in which a monitor that wrongly printed would show


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="answered-line-"))
    repository, state = work / "repo", work / "herdr.json"
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
        pane_environment = {**environment, "HERDR_PANE_ID": pane}
        done = subprocess.run(replay_probe.as_pane([USE_BOARD, *argv], pane, pane_environment, work / "stand-in"), cwd=repository, env=pane_environment, capture_output=True, text=True)
        return done.stdout.strip()

    def heartbeat():
        with (work / "monitor.log").open("w") as log:
            pane_environment = {**environment, "HERDR_PANE_ID": "w1:p2"}
            live = subprocess.Popen(replay_probe.as_pane([sys.executable, MONITOR], "w1:p2", pane_environment, work / "stand-in"), cwd=repository, env=pane_environment, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            time.sleep(QUIET_SECONDS)
            os.killpg(live.pid, signal.SIGKILL)
            live.wait()
        return (work / "monitor.log").read_text()

    number = use("w1:p1", "file", "--title", "Answer a held task", "--body", str(replay_probe.write_text(work, "body.md", "Answer a held task.\n")), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    use("w1:p1", "decide", number, "--decision", "c-worker holds this.", "--holders", "c-worker")
    asked = use("w1:p2", "comment", number, "--blocked", "which way")
    use("w1:p1", "decide", number, "--decision", "take the first way.", "--by", "c-manager", "--answers", asked)
    cases = {}
    saw = heartbeat()
    cases["unacted"] = (saw.count(f"answered #{number}") == 1, saw)
    use("w1:p2", "comment", number, "--reported", "took the first way")
    saw = heartbeat()
    cases["acted"] = (f"answered #{number}" not in saw, saw)
    for name, (passed, text) in cases.items():
        print(f"ok {name}" if passed else f"fail {name}: {text.strip()}", flush=True)
    ok = all(passed for passed, _ in cases.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
