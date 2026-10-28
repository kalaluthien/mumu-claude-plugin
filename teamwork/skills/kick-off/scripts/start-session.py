#!/usr/bin/env python3
"""Start a named agent session in herdr and send it its kick-off, placed by its role, which its kick-off arguments name:
a worker or sentinel in a new tab of its manager's workspace, a successor `<p>-next` of `succeed <p>` in a new tab of p's,
any other manager in a new workspace of its own. `--allow` turns a tool on that its role has off.

usage: start-session.py <name> <cwd> <kick-off arguments> --model <model> --effort <effort> [--allow <tool>]..."""
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import agent  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402
import usage_parser  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("START_SESSION_TIMEOUT", 120)), 1.0


def wait(name, ready, nudge, what):
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if ready(session.agent(name) or {}):
            return
        nudge(session.screen(name))
        time.sleep(POLL)
    raise RuntimeError(f"{name} {what} after {TIMEOUT:g}s")


def trusted(folder):
    """True when FOLDER is the repository root or under its worktrees; the root is the main checkout's, also from a worktree."""
    git = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    if git.returncode:  # no repository here: no folder is inside it
        return False
    root = pathlib.Path(git.stdout.strip()).resolve().parent
    return folder == root or root / ".claude" / "worktrees" in folder.parents


def accept_trust(name, cwd, kickoff):
    if not trusted(pathlib.Path(cwd)):  # a trust the owner never gave stays theirs to give
        sys.exit(f"start-session.py: {name} waits at the folder trust dialog for {cwd}, outside this repository and its worktrees; "
                 f"the owner must accept it in its pane (`{session.LOOK.format(name)}`), then send it its kick-off: {kickoff}")
    session.send_keys(name, *agent.TRUST[1])


def placement(name, args, role, listed):
    """The workspace NAME joins, or None for a new one of its own, or the reason it cannot start; no caller picks, so none picks wrong."""
    words = args.split()
    live = {listed_agent.get("name"): listed_agent for listed_agent in listed}
    if role != "manager":
        manager = words[3] if len(words) > 3 and words[2] == "manager" else None
        if manager not in live:
            return None, f"{manager} is not live: its {role} {name} sits in its manager's workspace, so start that manager first."
        return live[manager]["workspace_id"], None
    if words[:1] != ["succeed"]:
        return None, None
    peer = words[1] if len(words) == 2 else ""
    if name != f"{peer}-next":
        return None, f"{name} is not named {peer}-next, as the successor of {peer} is."
    if peer not in live:
        return None, f"{peer} is not live: start {name} only while the manager it succeeds runs."
    # a predecessor crowded by another project's manager hands over into a workspace of its own
    return (None if team_names.crowding(live[peer], listed) else live[peer]["workspace_id"]), None


def main(args):
    parser = usage_parser.parser(__doc__, prog="start-session.py", allow_abbrev=False)
    for field in ("name", "cwd", "args"):
        parser.add_argument(field)
    parser.add_argument("--model", required=True)  # no default: the caller picks per role
    parser.add_argument("--effort", required=True)
    parser.add_argument("--allow", action="append", default=[], metavar="TOOL")  # its subagents lack a tool their session lacks: grant it per backlog
    options = parser.parse_args(args)
    settings = team_settings.load(options.cwd)  # the session's repository, not this process's working folder
    for line in settings["warnings"]:
        print(line, file=sys.stderr)
    role = next((candidate for candidate in ("worker", "sentinel") if options.args.startswith(candidate + " ")), "manager")
    role_off = settings["tools_off"].get(role, [])
    if stray := sorted(set(options.allow) - set(role_off)):
        rule = f"--allow {', '.join(stray)}: not a tool this role has off, which is {', '.join(role_off) or 'none'}"
        if settings["refuse"]:
            print(f"start-session.py: {rule}", file=sys.stderr)
            return 2
        print(team_settings.warning(rule + "; it is ignored."), file=sys.stderr)
    off = [tool for tool in role_off if tool not in options.allow]
    listed = session.sessions()[0]
    if any(listed_agent.get("name") == options.name for listed_agent in listed):
        sys.exit(f"start-session.py: {options.name} is already live: hand it the work instead of starting another.")
    workspace, refusal = placement(options.name, options.args, role, listed)
    if refusal:
        sys.exit(f"start-session.py: {refusal}")
    text = agent.kickoff(options.args)
    trust = agent.TRUST[0]
    try:
        cwd = str(pathlib.Path(options.cwd).resolve())
        place = session.open_tab(workspace, cwd, options.name) if workspace else session.open_workspace(cwd, team_names.project(options.name))
        session.rename(place, options.name)
        pane = place["pane_id"]
        session.start(options.name, pane, agent.KIND, agent.command(options.name, str(ROOT), options.model, options.effort, off), TIMEOUT)
        # from here the name is the target, which herdr resolves on each call, since it may move the pane
        wait(options.name, lambda state: state.get("interactive_ready") and state.get("agent_status") != "blocked",  # trust dialog
             lambda screen: trust in screen and accept_trust(options.name, cwd, text), "not ready")
        session.prompt(options.name, text)  # the one prompt a session is sent: its kick-off
        wait(options.name, lambda state: state.get("agent_status") not in (None, "idle"),  # typed but unsent: press Enter
             lambda screen: text[:40] in screen and session.send_keys(options.name, "enter"), "never took its kick-off")
    except RuntimeError as e:
        sys.exit(f"start-session.py: {e}. Look at its pane with `{session.LOOK.format(options.name)}` before starting it again.")
    where = f"a new tab of workspace {workspace}" if workspace else "a new workspace of its own"
    print(f"{options.name} started in {where} (pane {pane}) and took its kick-off.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
