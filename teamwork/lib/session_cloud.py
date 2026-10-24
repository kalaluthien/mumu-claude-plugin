"""Probe stub, never merged: a cloud session as the session port's adapter, its name read from ~/.teamwork-name, which the worker writes."""
import os
import pathlib

LOOK = "claude.ai/code session page"
EMPTY = "no cloud session name; write it to ~/.teamwork-name."


def sessions(session_id=None):
    path = pathlib.Path.home() / ".teamwork-name"
    name = path.read_text().strip() if path.exists() else os.environ.get("TEAMWORK_NAME", "")
    me = {"name": name, "agent_status": "working"} if name else {}
    return [me] if me else [], me


def agent(name):
    return next((a for a in sessions()[0] if a.get("name") == name), None)


def screen(pane):
    return ""


def tabs(workspace):
    return []


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    raise RuntimeError(f"session_cloud stub has no {name}")
