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


def members(me, listed):
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")]
