#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
sys.path.insert(0, str(ROOT / "lib"))
import herdr_agents  # noqa: E402
from json_command import run  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("START_SESSION_TIMEOUT", 120)), 1.0
# claude.ai connectors (Gmail, Drive, Notion...) serve no teamwork role, and their tool list costs ~5k tokens every turn
SETTINGS = json.dumps({"disableClaudeAiConnectors": True})
# no role publishes pages, a worker asks the owner through its manager, a manager orchestrates by hand: each tool's description costs ~2-11k tokens
TOOLS_OFF = {"worker": "Artifact,AskUserQuestion", "manager": "Artifact,Workflow"}


def herdr(*argv):
    out = run("herdr", *argv)
    if out is None:
        raise RuntimeError(f"herdr {' '.join(argv[:2])} failed")
    return out["result"]


def open_pane(name, cwd, own_workspace, workspace):
    into = [] if own_workspace else ["--workspace", workspace or herdr("pane", "get", os.environ["HERDR_PANE_ID"])["pane"]["workspace_id"]]
    pane = herdr("workspace" if own_workspace else "tab", "create", *into, "--cwd", cwd, "--label", name.removesuffix("-manager") if own_workspace else name, "--no-focus")["root_pane"]
    run("herdr", "tab", "rename", pane["tab_id"], name)
    run("herdr", "pane", "rename", pane["pane_id"], name)
    return pane["pane_id"]


def wait(name, pane, ready, nudge, what):
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if ready(herdr_agents.agent(name) or {}):
            return
        nudge(herdr_agents.screen(pane))
        time.sleep(POLL)
    raise RuntimeError(f"{name} {what} after {TIMEOUT:g}s")


def start(a, pane):
    deadline = time.time() + TIMEOUT
    while True:
        p = subprocess.run(["herdr", "agent", "start", a.name, "--kind", "claude", "--pane", pane, "--", "--name", a.name,
                            "--plugin-dir", str(ROOT), "--model", a.model, "--effort", a.effort,
                            "--settings", SETTINGS, "--disallowedTools", TOOLS_OFF["worker" if a.args.startswith("worker ") else "manager"]],
                           capture_output=True, text=True)
        out = p.stdout + p.stderr
        if not p.returncode or '"agent_not_ready"' in out:  # not ready: the trust dialog holds it
            return
        if '"agent_pane_busy"' not in out or time.time() >= deadline:  # busy: the shell is still starting
            raise RuntimeError(f"herdr agent start: {(p.stderr or p.stdout).strip()}")
        time.sleep(POLL)


parser = argparse.ArgumentParser(prog="start-session.py", allow_abbrev=False)
for arg in ("name", "cwd", "args"):
    parser.add_argument(arg)
where_to = parser.add_mutually_exclusive_group()
where_to.add_argument("--team", action="store_true")
where_to.add_argument("--beside", metavar="AGENT")
parser.add_argument("--model", required=True)  # no default: the caller picks per role
parser.add_argument("--effort", required=True)
a = parser.parse_args()
if herdr_agents.agent(a.name):
    sys.exit(f"start-session.py: {a.name} is already live: hand it the work instead of starting another.")
peer = herdr_agents.agent(a.beside) if a.beside else {}  # a peer manager's successor sits in its workspace, alone with its workers
if peer is None:
    sys.exit(f"start-session.py: {a.beside} is not live: start {a.name} without --beside.")
text = f"/teamwork:kick-off {a.args}"
try:
    pane = open_pane(a.name, str(pathlib.Path(a.cwd).resolve()), a.team, peer.get("workspace_id"))
    start(a, pane)
    wait(a.name, pane, lambda s: s.get("interactive_ready") and s.get("agent_status") != "blocked",  # trust dialog
         lambda screen: "Yes, I trust this folder" in screen and run("herdr", "agent", "send-keys", pane, "down", "enter"),
         "not ready")
    run("herdr", "agent", "prompt", pane, text)  # the one prompt a session is sent: its kick-off
    wait(a.name, pane, lambda s: s.get("agent_status") not in (None, "idle"),  # typed but unsent: press Enter
         lambda screen: text[:40] in screen and run("herdr", "agent", "send-keys", pane, "enter"), "never took its kick-off")
except RuntimeError as e:
    sys.exit(f"start-session.py: {e}. Look at its pane with `herdr agent read {a.name}` before starting it again.")
where = "a new workspace of its own" if a.team else f"a new tab of {a.beside}'s workspace" if a.beside else "a new tab of your workspace"
print(f"{a.name} started in {where} (pane {pane}) and took its kick-off.")
