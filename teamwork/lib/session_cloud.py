"""A Claude Code cloud session as the session port's adapter: the session sees only itself, its name read from
~/.teamwork-name, which the worker writes when it names itself, since a cloud container has no herdr and lists no other session."""
import pathlib

LOOK = "claude --teleport <session id>"
EMPTY = "no cloud session name; write it to ~/.teamwork-name."
NEEDS = ()
NAME = pathlib.Path.home() / ".teamwork-name"


def sessions(session_id=None):
    name = NAME.read_text().strip() if NAME.exists() else ""
    me = {"name": name, "agent_status": "working"} if name else {}
    return [me] if me else [], me


def agent(name):
    return next((a for a in sessions()[0] if a.get("name") == name), None)


def screen(pane):
    return ""


def tabs(workspace):
    return []


def __getattr__(name):
    # each write the port names needs a host that runs other sessions, which a cloud container is not
    if name.startswith("__"):
        raise AttributeError(name)
    raise RuntimeError(f"a cloud session cannot {name}: start or close cloud sessions from a local session")
