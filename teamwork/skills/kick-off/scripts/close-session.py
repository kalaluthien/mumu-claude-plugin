#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import team  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("CLOSE_SESSION_TIMEOUT", 3600)), 1.0
# Claude Code may ask these on /exit; each key is the answer that exits without saving anything
DIALOGS = [
    ("Background work is running", "enter"),  # first option: Exit
    ("unsent feedback draft", "esc"),  # Esc to discard and exit
    ("d to discard", "d"),  # the drafts list, reached by Enter
    ("No feedback drafts queued", "esc"),  # the empty panel after `d`
]


def close(name):
    deadline = time.time() + TIMEOUT
    while (a := team.agent(name)) and a.get("agent_status") == "working":
        if time.time() >= deadline:
            sys.exit(f"close-session.py: {name} still at work after {TIMEOUT:g}s; nothing closed.")
        time.sleep(POLL)
    if not a:
        return print(f"{name} is not live; nothing to close.")
    pane, tab, workspace = a["pane_id"], a["tab_id"], a["workspace_id"]
    if a.get("agent_status") != "blocked":  # a blocked session already shows a dialog and refuses a prompt
        team.run("herdr", "agent", "prompt", pane, "/exit")
    answered = set()
    while team.agent(name) and time.time() < deadline:
        screen = team.screen(pane)
        for text, key in DIALOGS:
            if text in screen and text not in answered:
                team.run("herdr", "agent", "send-keys", pane, key)
                answered.add(text)
                break
        time.sleep(POLL)
    last = len((team.run("herdr", "tab", "list", "--workspace", workspace) or {}).get("result", {}).get("tabs", [])) <= 1
    team.run("herdr", *(("workspace", "close", workspace) if last else ("tab", "close", tab)))
    print(f"{name} exited and its {'workspace' if last else 'tab'} closed.")


if len(sys.argv) != 2:
    sys.exit("usage: close-session.py <name>")
name = sys.argv[1]
own = (team.agent(name) or {}).get("pane_id", "") == os.environ.get("HERDR_PANE_ID")
if own and not os.environ.get("CLOSE_SESSION_DETACHED"):  # detached, so it outlives the Bash call that asked for it
    subprocess.Popen([sys.executable, __file__, name], env={**os.environ, "CLOSE_SESSION_DETACHED": "1"},
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"{name} closes once this turn ends.")
else:
    close(name)
