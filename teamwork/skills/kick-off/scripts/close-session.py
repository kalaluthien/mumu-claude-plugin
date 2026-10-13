#!/usr/bin/env python3
"""Close the session NAME: once its turn ends, `/exit` it, answering each exit dialog, and close its tab, or its
workspace when the tab was the workspace's last.

usage: close-session.py <name>

Closing your own session runs detached, so it outlives the Bash call that asked for it."""
import json
import os
import subprocess
import sys
import time

TIMEOUT, POLL = float(os.environ.get("CLOSE_SESSION_TIMEOUT", 3600)), 1.0
# (screen text, key) per exit dialog Claude Code shows
DIALOGS = [
    ("Background work is running", "enter"),  # first option: Exit
    ("unsent feedback draft", "esc"),  # Esc to discard and exit
    ("d to discard", "d"),  # the drafts list, reached by Enter
    ("No feedback drafts queued", "esc"),  # the empty panel after `d`
]


def herdr(*argv):
    return subprocess.run(["herdr", *argv], capture_output=True, text=True).stdout


def agent(name):
    try:
        return next((a for a in json.loads(herdr("agent", "list"))["result"]["agents"] if a.get("name") == name), None)
    except (ValueError, KeyError):
        return None


def close(name):
    deadline = time.time() + TIMEOUT
    while (a := agent(name)) and a.get("agent_status") == "working":
        if time.time() >= deadline:
            sys.exit(f"close-session.py: {name} still at work after {TIMEOUT:g}s; nothing closed.")
        time.sleep(POLL)
    if not a:
        return print(f"{name} is not live; nothing to close.")
    pane, tab, workspace = a["pane_id"], a["tab_id"], a["workspace_id"]
    if a.get("agent_status") != "blocked":  # a blocked session already shows a dialog and refuses a prompt
        herdr("agent", "prompt", pane, "/exit")
    answered = set()
    while agent(name) and time.time() < deadline:
        screen = herdr("agent", "read", pane, "--source", "visible")
        for text, key in DIALOGS:
            if text in screen and text not in answered:
                herdr("agent", "send-keys", pane, key)
                answered.add(text)
                break
        time.sleep(POLL)
    tabs = json.loads(herdr("tab", "list", "--workspace", workspace) or "{}").get("result", {}).get("tabs", [])
    herdr(*(("workspace", "close", workspace) if len(tabs) <= 1 else ("tab", "close", tab)))
    print(f"{name} exited and its {'workspace' if len(tabs) <= 1 else 'tab'} closed.")


def main(argv):
    if len(argv) != 1:
        sys.exit("usage: close-session.py <name>")
    name = argv[0]
    own = agent(name) and agent(name).get("pane_id") == os.environ.get("HERDR_PANE_ID")
    if own and not os.environ.get("CLOSE_SESSION_DETACHED"):
        subprocess.Popen([sys.executable, __file__, name], env={**os.environ, "CLOSE_SESSION_DETACHED": "1"},
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return print(f"{name} closes once this turn ends.")
    close(name)


if __name__ == "__main__":
    main(sys.argv[1:])
