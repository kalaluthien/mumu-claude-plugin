#!/usr/bin/env python3
import argparse
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
sys.path.insert(0, str(ROOT / "lib"))
import agent  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("START_SESSION_TIMEOUT", 120)), 1.0


def wait(name, pane, ready, nudge, what):
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if ready(session.agent(name) or {}):
            return
        nudge(session.screen(pane))
        time.sleep(POLL)
    raise RuntimeError(f"{name} {what} after {TIMEOUT:g}s")


parser = argparse.ArgumentParser(prog="start-session.py", allow_abbrev=False)
for arg in ("name", "cwd", "args"):
    parser.add_argument(arg)
where_to = parser.add_mutually_exclusive_group()
where_to.add_argument("--team", action="store_true")
where_to.add_argument("--beside", metavar="AGENT")
parser.add_argument("--model", required=True)  # no default: the caller picks per role
parser.add_argument("--effort", required=True)
parser.add_argument("--allow", action="append", default=[], metavar="TOOL")  # its subagents lack a tool their session lacks: grant it per backlog
a = parser.parse_args()
settings = team_settings.load(a.cwd)  # the session's repository, not this process's working folder
for line in settings["warnings"]:
    print(line, file=sys.stderr)
role_off = settings["tools_off"].get("worker" if a.args.startswith("worker ") else "manager", [])
if stray := sorted(set(a.allow) - set(role_off)):
    rule = f"--allow {', '.join(stray)}: not a tool this role has off, which is {', '.join(role_off) or 'none'}"
    if settings["refuse"]:
        parser.error(rule)
    print(team_settings.warning(rule + "; it is ignored."), file=sys.stderr)
off = [t for t in role_off if t not in a.allow]
if session.agent(a.name):
    sys.exit(f"start-session.py: {a.name} is already live: hand it the work instead of starting another.")
peer = session.agent(a.beside) if a.beside else {}  # a peer manager's successor sits in its workspace, alone with its workers
if peer is None:
    sys.exit(f"start-session.py: {a.beside} is not live: start {a.name} without --beside.")
text = agent.kickoff(a.args)
trust, accept = agent.TRUST
try:
    cwd = str(pathlib.Path(a.cwd).resolve())
    place = session.open_workspace(cwd, team_names.project(a.name)) if a.team else session.open_tab(peer.get("workspace_id"), cwd, a.name)
    session.rename(place, a.name)
    pane = place["pane_id"]
    session.start(a.name, pane, agent.KIND, agent.command(a.name, str(ROOT), a.model, a.effort, off), TIMEOUT)
    wait(a.name, pane, lambda s: s.get("interactive_ready") and s.get("agent_status") != "blocked",  # trust dialog
         lambda screen: trust in screen and session.send_keys(pane, *accept), "not ready")
    session.prompt(pane, text)  # the one prompt a session is sent: its kick-off
    wait(a.name, pane, lambda s: s.get("agent_status") not in (None, "idle"),  # typed but unsent: press Enter
         lambda screen: text[:40] in screen and session.send_keys(pane, "enter"), "never took its kick-off")
except RuntimeError as e:
    sys.exit(f"start-session.py: {e}. Look at its pane with `{session.LOOK.format(a.name)}` before starting it again.")
where = "a new workspace of its own" if a.team else f"a new tab of {a.beside}'s workspace" if a.beside else "a new tab of your workspace"
print(f"{a.name} started in {where} (pane {pane}) and took its kick-off.")
