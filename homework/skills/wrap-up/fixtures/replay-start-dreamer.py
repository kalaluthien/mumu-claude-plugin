#!/usr/bin/env python3
"""Run start-dreamer.py against a stand-in herdr that answers `agent_pane_busy` first, and print one line per step and
`probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: replay-start-dreamer.py"""
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
    log.write(" ".join(words[:2]) + "\\n")
def reply(result):
    print(json.dumps({"result": result}))
if words[:2] == ["agent", "list"]:
    reply({"agents": []})
elif words[:2] == ["pane", "get"]:
    reply({"pane": {"workspace_id": "w1"}})
elif words[:2] == ["tab", "create"]:
    reply({"tab": {"tab_id": "w1:t2"}, "root_pane": {"pane_id": "w1:p2"}})
elif words[:2] == ["agent", "start"]:
    with open(os.path.join(folder, "calls")) as log:
        tries = log.read().count("agent start")
    if tries <= int(os.environ["HOMEWORK_START_DREAMER_BUSY"]):
        print(json.dumps({"error": {"code": "agent_pane_busy", "message": "not an available shell"}}))
        sys.exit(1)
    reply({"agent": {"name": words[2]}})
else:
    reply({})
"""
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}")


def run(busy):
    """Exit code, output and herdr calls of one start while the first `busy` starts answer busy."""
    with tempfile.TemporaryDirectory() as folder:
        bin_folder = pathlib.Path(folder, "bin")
        bin_folder.mkdir()
        herdr = bin_folder / "herdr"
        herdr.write_text(STAND_IN)
        herdr.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_folder}{os.pathsep}{os.environ['PATH']}", HOMEWORK_START_DREAMER_FOLDER=folder, HOMEWORK_START_DREAMER_BUSY=str(busy),
                   HERDR_PANE_ID="w1:p1", HOMEWORK_START_DREAMER_WAIT="2", HOMEWORK_START_DREAMER_POLL="0.05")
        done = subprocess.run([sys.executable, SCRIPT, folder, folder, folder, "14", "8"], capture_output=True, text=True, env=env, cwd=folder, timeout=60)
        calls = pathlib.Path(folder, "calls").read_text().splitlines()
    return done.returncode, done.stdout + done.stderr, calls


code, out, calls = run(2)
step("busy twice, then started", code == 0 and out.startswith("started "), f"exit {code}: {out}")
step("started leaves its tab open", "tab close" not in calls, str(calls))
code, out, calls = run(10**6)
step("busy past the deadline fails", code == 1 and out.startswith("failed to start"), f"exit {code}: {out}")
step("failed start closes its tab", calls.count("tab create") == 1 and calls[-1] == "tab close", str(calls))
print(f"probe: {sum(results)} of {len(results)} steps pass")
sys.exit(0 if all(results) else 1)
