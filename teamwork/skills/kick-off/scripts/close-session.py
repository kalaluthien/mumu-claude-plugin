#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import agent  # noqa: E402
import session  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("CLOSE_SESSION_TIMEOUT", 3600)), 1.0


def close(name):
    deadline = time.time() + TIMEOUT
    while (a := session.agent(name)) and a.get("agent_status") == "working":
        if time.time() >= deadline:
            sys.exit(f"close-session.py: {name} still at work after {TIMEOUT:g}s; nothing closed.")
        time.sleep(POLL)
    if not a:
        return print(f"{name} is not live; nothing to close.")
    pane = a["pane_id"]
    if a.get("agent_status") != "blocked":  # a blocked session already shows a dialog and refuses a prompt
        session.prompt(pane, agent.EXIT)
    answered = set()
    while session.agent(name) and time.time() < deadline:
        screen = session.screen(pane)
        for text, key in agent.DIALOGS:
            if text in screen and text not in answered:
                session.send_keys(pane, key)
                answered.add(text)
                break
        time.sleep(POLL)
    if session.agent(name):
        sys.exit(f"close-session.py: {name} is still live after {TIMEOUT:g}s; its tab stays open.")
    print(f"{name} exited and its {session.close(a)} closed.")


if len(sys.argv) != 2:
    sys.exit("usage: close-session.py <name>")
name = sys.argv[1]
own = session.sessions()[1].get("name") == name
if own and not os.environ.get("CLOSE_SESSION_DETACHED"):  # detached, so it outlives the Bash call that asked for it
    subprocess.Popen([sys.executable, __file__, name], env={**os.environ, "CLOSE_SESSION_DETACHED": "1"},
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"{name} closes once this turn ends.")
else:
    close(name)
