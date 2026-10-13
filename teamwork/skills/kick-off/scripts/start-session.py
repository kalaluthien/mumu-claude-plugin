#!/usr/bin/env python3
"""usage: start-session.py <name> <cwd> <args> --model M --effort E [--team]

Start a Claude session NAME in CWD, its first turn `/teamwork:kick-off ARGS`, in a new tab of the caller's workspace or
with `--team` a workspace of its own; its tab, first pane, agent and Claude session all take NAME."""
import argparse
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
sys.path.insert(0, str(ROOT / "lib"))
import team  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("START_SESSION_TIMEOUT", 120)), 1.0


def herdr(*argv):
    out = team.run("herdr", *argv)
    if out is None:
        raise RuntimeError(f"herdr {' '.join(argv[:2])} failed")
    return out["result"]


def open_pane(name, cwd, own_workspace):
    """The first pane of a new workspace, or of a new tab in the caller's workspace, named `name`."""
    if own_workspace:
        pane = herdr("workspace", "create", "--cwd", cwd, "--label", name, "--no-focus")["root_pane"]
    else:
        workspace = herdr("pane", "get", os.environ["HERDR_PANE_ID"])["pane"]["workspace_id"]
        pane = herdr("tab", "create", "--workspace", workspace, "--cwd", cwd, "--label", name, "--no-focus")["root_pane"]
    team.run("herdr", "tab", "rename", pane["tab_id"], name)
    team.run("herdr", "pane", "rename", pane["pane_id"], name)
    return pane["pane_id"]


def wait(name, pane, ready, nudge, what):
    """Poll `name` until `ready(agent)`, calling `nudge(screen)` each round, or fail naming `what`."""
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if ready(team.agent(name) or {}):
            return
        nudge(team.screen(pane))
        time.sleep(POLL)
    raise RuntimeError(f"{name} {what} after {TIMEOUT:g}s")


def main(argv):
    parser = argparse.ArgumentParser(prog="start-session.py", allow_abbrev=False)
    for arg in ("name", "cwd", "args"):
        parser.add_argument(arg)
    parser.add_argument("--team", action="store_true")
    parser.add_argument("--model", required=True)  # no default: the caller picks per role
    parser.add_argument("--effort", required=True)
    a = parser.parse_args(argv)
    if team.agent(a.name):
        sys.exit(f"start-session.py: {a.name} is already live: SendMessage it instead of starting another.")
    text = f"/teamwork:kick-off {a.args}"
    try:
        pane = open_pane(a.name, str(pathlib.Path(a.cwd).resolve()), a.team)
        team.run("herdr", "agent", "start", a.name, "--kind", "claude", "--pane", pane, "--", "--name", a.name,
                 "--plugin-dir", str(ROOT), "--model", a.model, "--effort", a.effort)
        wait(a.name, pane, lambda s: s.get("interactive_ready") and s.get("agent_status") != "blocked",  # trust dialog
             lambda screen: "Yes, I trust this folder" in screen and team.run("herdr", "agent", "send-keys", pane, "down", "enter"),
             "not ready")
        team.run("herdr", "agent", "prompt", pane, text)  # the one prompt a session is sent: its kick-off
        wait(a.name, pane, lambda s: s.get("agent_status") not in (None, "idle"),  # typed but unsent: press Enter
             lambda screen: text[:40] in screen and team.run("herdr", "agent", "send-keys", pane, "enter"), "never took its kick-off")
    except RuntimeError as e:
        sys.exit(f"start-session.py: {e}. Look at its pane with `herdr agent read {a.name}` before starting it again.")
    where = "a new workspace of its own" if a.team else "a new tab of your workspace"
    print(f"{a.name} started in {where} (pane {pane}) and took its kick-off; it answers by SendMessage.")


if __name__ == "__main__":
    main(sys.argv[1:])
