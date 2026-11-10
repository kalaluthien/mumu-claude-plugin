#!/usr/bin/env python3
"""Start workers against a fake herdr (fake-herdr/herdr beside this file) with `--steer` of two keys, of none, of a key beside one that takes its line alone, of an unknown key and of lines over the cap, and print `PASS` when
the prompt of the first ends with exactly the two lines of the steering table and equals the lines `print-steering.py` prints for those keys, the prompt of the second equals the plain kick-off, and every refused start exits 2 with no agent started, else `FAIL: <what differed>`.

usage: replay-steering-start.py"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # the plugin
KICKOFF = "Run the teamwork:kick-off skill with these arguments: "
LONG_ROW = "| long | any | a case with a line over the cap | " + " ".join(["word"] * 120) + " |\n"


def table_line(key):
    return re.search(rf"^\| {key} \| .*? \| .*? \| (.*) \|$", (ROOT / "skills/kick-off/assets/handoff-worker-prompt.md").read_text(), re.M)[1]


def run(plugin, work, *command):
    state, log = work / "state.json", work / "log"
    state.write_text(json.dumps({"n": 10, "tabs": [], "agents": [
        {"name": "teamwork-manager", "pane_id": "w1:p2", "tab_id": "w1:t2", "workspace_id": "w1", "agent": "claude", "agent_status": "idle", "interactive_ready": True}]}))
    log.write_text("")
    environment = {**os.environ, "PATH": f"{HERE / 'fake-herdr'}:{os.environ['PATH']}", "TEAMWORK_FAKE_HERDR_STATE": str(state), "TEAMWORK_FAKE_HERDR_LOG": str(log), "TEAMWORK_START_SESSION_TIMEOUT": "3"}
    done = subprocess.run([str(plugin / "skills/kick-off/scripts" / command[0]), *command[1:]], cwd=work, env=environment, capture_output=True, text=True)
    prompts = [call[3] for call in map(json.loads, log.read_text().splitlines()) if call[:2] == ["agent", "prompt"]]
    return done, prompts


def start(name, *steering):
    return ["start-session.py", name, "/tmp", f"worker {name} manager teamwork-manager https://example.com/1", "--model", "haiku", "--effort", "medium", *steering]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="steering-start-")).resolve()
    copy = work / "teamwork"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
    with open(copy / "skills/kick-off/assets/handoff-worker-prompt.md", "a") as table:
        table.write(LONG_ROW)
    wanted = f"{table_line('visible-change')} {table_line('new-mechanism')}"
    plain = KICKOFF + "worker a-worker manager teamwork-manager https://example.com/1"
    problems = []
    done, prompts = run(ROOT, work, *start("a-worker", "--steer", "visible-change", "--steer", "new-mechanism"))
    told = subprocess.run([str(ROOT / "skills/kick-off/scripts/print-steering.py"), "visible-change", "new-mechanism"], capture_output=True, text=True).stdout.strip()
    if prompts != [f"{plain} — {wanted}"] or told != wanted:
        problems.append(f"two keys sent {prompts}, print-steering printed {told!r}")
    done, prompts = run(ROOT, work, *start("a-worker"))
    if prompts != [plain]:
        problems.append(f"no key sent {prompts}")
    for refused in (("research", "cleanup"), ("nope",), ("long",)):
        done, prompts = run(copy, work, *start("a-worker", *[word for key in refused for word in ("--steer", key)]))
        if done.returncode != 2 or prompts:
            problems.append(f"--steer {' '.join(refused)} exited {done.returncode} and sent {prompts}")
    shutil.rmtree(work, ignore_errors=True)
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
