#!/usr/bin/env python3
"""Run start-dreamer.py against a stand-in herdr that holds a finished or working dreamer and answers `agent_name_taken` until its tab is closed, and print one line per step and
`probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: replay-finished-dreamer.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = str(HERE.parent / "scripts" / "start-dreamer.py")
STAND_IN = """#!/usr/bin/env python3
import json, os, sys
folder = os.environ["HOMEWORK_START_DREAMER_FOLDER"]
words = sys.argv[1:]
with open(os.path.join(folder, "calls"), "a") as log:
    log.write(" ".join(words[:3] if words[:2] == ["tab", "close"] else words[:2]) + "\\n")
def reply(result):
    print(json.dumps({"result": result}))
closed = "tab close w1:t9" in open(os.path.join(folder, "calls")).read()
if words[:2] == ["agent", "list"]:
    status = os.environ["HOMEWORK_START_DREAMER_STATUS"]
    reply({"agents": [] if closed and status == "done" else [{"name": "memory-repeats-habit-dreamer", "agent_status": status, "tab_id": "w1:t9", "pane_id": "w1:p9"}]})
elif words[:2] == ["pane", "get"]:
    reply({"pane": {"workspace_id": "w1"}})
elif words[:2] == ["tab", "create"]:
    reply({"tab": {"tab_id": "w1:t2"}, "root_pane": {"pane_id": "w1:p2"}})
elif words[:2] == ["agent", "start"]:
    with open(os.path.join(folder, "calls")) as log:
        late = log.read().count("agent start") <= 1 and closed
    if not closed or late:
        print(json.dumps({"error": {"code": "agent_name_taken", "message": "name taken"}}))
        sys.exit(1)
    reply({"agent": {"name": words[2]}})
else:
    reply({})
"""
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}")


def run(status):
    """Exit code, output and herdr calls of one start while a dreamer of that status holds the name, the name freed one start late."""
    with tempfile.TemporaryDirectory() as folder:
        bin_folder = pathlib.Path(folder, "bin")
        bin_folder.mkdir()
        herdr = bin_folder / "herdr"
        herdr.write_text(STAND_IN)
        herdr.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_folder}{os.pathsep}{os.environ['PATH']}", HOMEWORK_START_DREAMER_FOLDER=folder, HERDR_PANE_ID="w1:p1", HOMEWORK_START_DREAMER_STATUS=status,
                   HOMEWORK_START_DREAMER_WAIT="2", HOMEWORK_START_DREAMER_POLL="0.05")
        done = subprocess.run([sys.executable, SCRIPT, folder, folder, folder, "14", "8"], capture_output=True, text=True, env=env, cwd=folder, timeout=60)
        calls = pathlib.Path(folder, "calls").read_text().splitlines()
    return done.returncode, done.stdout + done.stderr, calls


code, out, calls = run("done")
step("finished dreamer replaced", code == 0 and out.startswith("started ") and "tab close w1:t9" in calls, f"exit {code}: {out} {calls}")
code, out, calls = run("working")
step("working dreamer left alone", code == 0 and out.startswith("held by ") and calls == ["agent list"], f"exit {code}: {out} {calls}")
print(f"probe: {sum(results)} of {len(results)} steps pass")
sys.exit(0 if all(results) else 1)
