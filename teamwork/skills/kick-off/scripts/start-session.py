#!/usr/bin/env python3
"""Start a Claude session named NAME in CWD and give it PROMPT as its first turn.

usage: start-session.py <name> <cwd> <prompt> [--team] [--model M] [--effort E] [-- <claude flags>]

The session gets a new tab in the caller's workspace, or with `--team` a new workspace of its own, and its tab, first
pane, agent and Claude session all take NAME, so one name finds it everywhere."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
TIMEOUT, POLL = float(os.environ.get("START_SESSION_TIMEOUT", 120)), 1.0


def herdr(*argv, check=True):
    p = subprocess.run(["herdr", *argv], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"herdr {' '.join(argv[:2])}: {(p.stderr or p.stdout).strip()}")
    return p


def result(*argv):
    return json.loads(herdr(*argv).stdout)["result"]


def agent(name):
    return next((a for a in result("agent", "list")["agents"] if a.get("name") == name), None)


def screen(pane):
    return herdr("agent", "read", pane, "--source", "visible", check=False).stdout


def open_pane(name, cwd, team):
    """The first pane of a new workspace, or of a new tab in the caller's workspace, named `name`."""
    if team:
        made = result("workspace", "create", "--cwd", cwd, "--label", name, "--no-focus")
    else:
        own = result("pane", "get", os.environ["HERDR_PANE_ID"])["pane"]["workspace_id"]
        made = result("tab", "create", "--workspace", own, "--cwd", cwd, "--label", name, "--no-focus")
    pane = made["root_pane"]
    herdr("tab", "rename", pane["tab_id"], name)
    herdr("pane", "rename", pane["pane_id"], name)
    return pane["pane_id"]


def launch(name, pane, claude_args):
    """Start Claude as agent `name` in `pane`, answering the folder-trust dialog, until it takes input."""
    p = herdr("agent", "start", name, "--kind", "claude", "--pane", pane, "--", *claude_args, check=False)
    if p.returncode and '"agent_not_ready"' not in p.stdout + p.stderr:  # not ready: the trust dialog holds it
        raise RuntimeError(f"herdr agent start: {(p.stderr or p.stdout).strip()}")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        a = agent(name)
        if a and a.get("interactive_ready") and a.get("agent_status") != "blocked":
            return
        if "Yes, I trust this folder" in screen(pane):
            herdr("agent", "send-keys", pane, "down", "enter")
        time.sleep(POLL)
    raise RuntimeError(f"{name} not ready after {TIMEOUT:g}s")


def deliver(name, pane, text):
    """Prompt `name` until its turn starts: Enter when the text sits typed but unsent, else the text again."""
    for attempt in range(3):
        if attempt and text[:40] in screen(pane):
            herdr("agent", "send-keys", pane, "enter")
        else:
            herdr("agent", "prompt", pane, text)
        deadline = time.time() + TIMEOUT / 3
        while time.time() < deadline:
            if (agent(name) or {}).get("agent_status") not in (None, "idle"):
                return
            time.sleep(POLL)
    raise RuntimeError(f"{name} never took its prompt")


def main(argv):
    flags = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    parser = argparse.ArgumentParser(prog="start-session.py", allow_abbrev=False)
    parser.add_argument("name")
    parser.add_argument("cwd")
    parser.add_argument("prompt")
    parser.add_argument("--team", action="store_true")
    parser.add_argument("--model", default="opus")
    parser.add_argument("--effort", default="medium")
    a = parser.parse_args(argv)
    if agent(a.name):
        sys.exit(f"start-session.py: {a.name} is already live: prompt it `see <url>` instead of starting another.")
    try:
        pane = open_pane(a.name, str(pathlib.Path(a.cwd).resolve()), a.team)
        launch(a.name, pane, ["--name", a.name, "--plugin-dir", str(ROOT), "--model", a.model, "--effort", a.effort, *flags])
        deliver(a.name, pane, a.prompt)
    except RuntimeError as e:
        sys.exit(f"start-session.py: {e}. Look at its pane with `herdr agent read {a.name}` before starting it again.")
    where = "a new workspace of its own" if a.team else "a new tab of your workspace"
    print(f"{a.name} started in {where} (pane {pane}) and took its prompt; it answers with `see <url>` when it needs you.")


if __name__ == "__main__":
    main(sys.argv[1:])
