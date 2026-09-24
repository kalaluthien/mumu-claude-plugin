#!/usr/bin/env python3
"""Close a worker in one call: its Claude session, the background-work dialog, its tab, its mission line and its own mission.

usage: worker-close.py <name>

Sends `/exit` to the agent herdr lists as `<name>`, and presses Enter once when
the "Background work is running" dialog shows, whose first option exits; then
waits until herdr no longer lists the agent, closes every tab labelled
`<name>`, and removes `SUBSCRIBE: <name> ...` from this session's mission
(`team.mission_file`), and deletes the worker's own mission, found by the
session id herdr lists as its `agent_session` before `/exit`; none found, none
deleted. An agent already gone skips to the tab. Prints
`closed <name>`. `WORKER_CLOSE_TIMEOUT` (60) and `WORKER_CLOSE_POLL` (1) are seconds.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

DIALOG = "Background work is running"


def run(*argv):
    """stdout of `argv`, raising with its stderr when it fails."""
    done = subprocess.run(argv, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def agent(name):
    """The agent herdr lists as `name`, or None."""
    return next((a for a in json.loads(run("herdr", "agent", "list"))["result"]["agents"] if a.get("name") == name), None)


def pane(name):
    """The pane of the agent herdr lists as `name`, or None."""
    a = agent(name)
    return a and a["pane_id"]


def exit_session(name, timeout, poll):
    """`/exit` the agent `name`, answering the background-work dialog once, and return once herdr no longer lists it."""
    target = pane(name)
    if target is None:
        return
    run("herdr", "agent", "prompt", target, "/exit")
    answered, deadline = False, time.time() + timeout
    while pane(name) is not None:
        if time.time() >= deadline:
            raise RuntimeError(f"{name} still running after {timeout:g}s; see `herdr agent read {target}`")
        if not answered and DIALOG in run("herdr", "agent", "read", target, "--lines", "40"):
            run("herdr", "agent", "send-keys", target, "enter")
            answered = True
        time.sleep(poll)


def main(argv):
    if len(argv) != 1:
        print("usage: worker-close.py <name>", file=sys.stderr)
        return 2
    name = argv[0]
    timeout, poll = float(os.environ.get("WORKER_CLOSE_TIMEOUT", 60)), float(os.environ.get("WORKER_CLOSE_POLL", 1))
    try:
        session = ((agent(name) or {}).get("agent_session") or {}).get("value")
        exit_session(name, timeout, poll)
        for tab in json.loads(run("herdr", "tab", "list"))["result"]["tabs"]:
            if tab.get("label") == name:
                run("herdr", "tab", "close", tab["tab_id"])
    except RuntimeError as e:
        print(f"worker-close.py: {e}", file=sys.stderr)
        return 1
    mission = team.mission_file()
    if mission is not None:
        team.unsubscribe(mission, name)
    own = team.mission_file(session) if session else None
    if own is not None:
        own.unlink(missing_ok=True)
    print(f"closed {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
