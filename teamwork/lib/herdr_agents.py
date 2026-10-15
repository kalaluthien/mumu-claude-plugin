"""The live Claude sessions herdr runs, and this session's own among them."""
import os
import subprocess

from json_command import run


def sessions(session_id=None):
    """Every live agent, and this session's own: its pane's, unless the pane runs another session, as a worker's child does."""
    listed = (run("herdr", "agent", "list") or {}).get("result", {}).get("agents", [])
    me = next((a for a in listed if a.get("pane_id") == os.environ.get("HERDR_PANE_ID")), {})
    own = not session_id or (me.get("agent_session") or {}).get("value") in (None, "", session_id)
    return listed, me if own else {}


def agent(name):
    return next((a for a in sessions()[0] if a.get("name") == name), None)


def screen(pane):
    return subprocess.run(["herdr", "agent", "read", pane, "--source", "visible"], capture_output=True, text=True).stdout


def role(name):
    """`manager` or `worker` by the name's suffix; None for a name with neither, a session outside any team, such as the owner's own."""
    return next((r for r in ("manager", "worker") if (name or "").endswith("-" + r)), None)


def project(manager):
    return manager.removesuffix("-manager")


def owns(name, branch):
    return branch == name or branch.startswith(name + "-")


def tabs(workspace):
    return (run("herdr", "tab", "list", "--workspace", workspace) or {}).get("result", {}).get("tabs", [])


def members(me, listed):
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")]
