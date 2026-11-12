#!/usr/bin/env python3
"""Start a named agent session in herdr and send it its kick-off, placed by its role, which its kick-off arguments name:
a worker or sentinel in a new tab of its manager's workspace, a successor `<p>-next` of `succeed <p>` in a new tab of p's,
any other manager in a new workspace of its own. `--allow` turns a tool on that its role has off.

usage: start-session.py <name> <cwd> <kick-off arguments> --model <model> --effort <effort> [--allow <tool>]... [--steer <key>]...

`--steer` puts the steering lines of those keys (print-steering.py lists them) after the kick-off arguments; a key it refuses, exit 2, starts nothing."""
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]  # this plugin, loaded into the new session too
sys.path.insert(0, str(ROOT / "lib"))
import agent  # noqa: E402
import session  # noqa: E402
import steering_lines  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402
import usage_parser  # noqa: E402

SUFFIXES = ("-worker", "-sentinel", "-manager", "-next")
FORMS = "`<task>-worker`, `<duty>-sentinel`, `<project>-manager` or `<manager>-next`"
TIMEOUT, POLL = float(os.environ.get("TEAMWORK_START_SESSION_TIMEOUT", 120)), 1.0


def wait(name, ready, nudge, what):
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if ready(session.agent(name) or {}):
            return
        nudge(session.screen(name))
        time.sleep(POLL)
    raise RuntimeError(f"{name} {what} after {TIMEOUT:g}s")


def look(name, pane):
    """The command that shows NAME's pane where herdr has it now, else PANE, where it was started."""
    return session.LOOK.format((session.agent(name) or {}).get("pane_id", pane))


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
                 f"the owner must accept it in its pane (`{look(name, None)}`), then send it its kick-off: {kickoff}")
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
    parser.add_argument("--allow", action="append", default=[], metavar="TOOL")  # its subagents lack a tool their session lacks: grant it per root task
    parser.add_argument("--steer", action="append", default=[], metavar="KEY")
    options = parser.parse_args(args)
    try:
        steering = steering_lines.lines(options.steer) if options.steer else ""
    except ValueError as e:
        print(f"start-session.py: {e}", file=sys.stderr)
        return 2
    settings = team_settings.load(options.cwd)  # the session's repository, not this process's working folder
    for line in settings["warnings"]:
        print(line, file=sys.stderr)
    role = next((candidate for candidate in ("worker", "sentinel") if options.args.startswith(candidate + " ")), "manager")
    named_role = "manager" if options.name.endswith(("-manager", "-next")) else options.name.rsplit("-", 1)[-1]
    if options.args.split()[4:6] == ["set", "remote"]:  # a stale kick-off line must fail, not start a herdr session where its sender expects a cloud one
        print("start-session.py: set remote: every session runs in herdr; leave out `set remote`.", file=sys.stderr)
        return 2
    if not options.name.endswith(SUFFIXES):  # the heartbeat, hooks and branch cleanup know a role by its name's suffix
        print(f"start-session.py: {options.name} ends in no role suffix: name it {FORMS}.", file=sys.stderr)
        return 2
    if named_role != role:  # a worker or sentinel read as a manager would get a workspace of its own, outside its team
        print(f"start-session.py: {options.name} is named a {named_role} but its kick-off arguments start a {role}: "
              f"a worker or sentinel kick-off begins `worker <name> manager <manager>` or `sentinel <name> manager <manager>`.", file=sys.stderr)
        return 2
    role_off = settings["tools_off"].get(role, [])
    if stray := sorted(set(options.allow) - set(role_off)):
        print(f"start-session.py: --allow {', '.join(stray)}: not a tool this role has off, which is {', '.join(role_off) or 'none'}", file=sys.stderr)
        return 2
    off = [tool for tool in role_off if tool not in options.allow]
    listed = session.sessions()[0]
    if any(listed_agent.get("name") == options.name for listed_agent in listed):
        sys.exit(f"start-session.py: {options.name} is already live: hand it the work instead of starting another.")
    workspace, refusal = placement(options.name, options.args, role, listed)
    if refusal:
        sys.exit(f"start-session.py: {refusal}")
    text = agent.kickoff(f"{options.args} — {steering}" if steering else options.args)
    trust = agent.TRUST[0]
    pane, sent = None, False
    try:
        cwd = str(pathlib.Path(options.cwd).resolve())
        place = session.open_tab(workspace, cwd, options.name) if workspace else session.open_workspace(cwd, team_names.project(options.name))
        session.rename(place, options.name)
        pane = place["pane_id"]
        session.start(options.name, pane, agent.KIND, agent.command(options.name, str(ROOT), options.model, options.effort, off), TIMEOUT)
        # from here the name is the target, which herdr resolves on each call, since it may move the pane
        wait(options.name, lambda state: state.get("interactive_ready") and state.get("agent_status") != "blocked",  # trust dialog
             lambda screen: trust in screen and accept_trust(options.name, cwd, text), "not ready")
        sent = session.prompt(options.name, text) is None  # the one prompt a session is sent: its kick-off
        wait(options.name, lambda state: state.get("agent_status") not in (None, "idle"),  # typed but unsent: press Enter
             lambda screen: text[:40] in screen and session.send_keys(options.name, "enter"), "never took its kick-off")
    except RuntimeError as e:
        if not session.agent(options.name):
            state = f"{options.name} is not live and got no kick-off; " + (f"look at its pane with `{look(options.name, pane)}` before starting it again" if pane else "no pane was opened for it")
        elif sent:
            state = f"{options.name} is live and its kick-off was typed, but it did not start on it; look at its pane with `{look(options.name, pane)}`, and start no second one"
        else:
            state = f"{options.name} is live and got no kick-off; start no second one, look at its pane with `{look(options.name, pane)}` and send it: {text}"
        sys.exit(f"start-session.py: {e}. {state}.")
    where = f"a new tab of workspace {workspace}" if workspace else "a new workspace of its own"
    print(f"{options.name} started in {where} (pane {pane}) and took its kick-off.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
