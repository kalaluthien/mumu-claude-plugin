#!/usr/bin/env python3
"""Close a named session once it stops working: send it its exit, answer the dialogs it shows, then close its tab.

usage: close-session.py <name>

A session closing itself runs detached, so it closes once the turn ends. CLOSE_SESSION_TIMEOUT (default 3600) bounds the
wait in seconds."""
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
    if a.get("agent_status") != "blocked":  # a blocked session already shows a dialog and refuses a prompt
        session.prompt(name, agent.EXIT)  # the name, which herdr resolves on each call, since it may move the pane
    answered = set()
    while (now := session.agent(name)) and time.time() < deadline:
        a, screen = now, session.screen(name)  # the latest read, whose tab close shuts
        for text, key in agent.DIALOGS:
            if text in screen and text not in answered:
                session.send_keys(name, key)
                answered.add(text)
                break
        time.sleep(POLL)
    if session.agent(name):
        sys.exit(f"close-session.py: {name} is still live after {TIMEOUT:g}s; its tab stays open.")
    print(f"{name} exited and its {session.close(a)} closed.")


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    name = args[0]
    own = session.sessions()[1].get("name") == name
    if own and not os.environ.get("CLOSE_SESSION_DETACHED"):  # detached, so it outlives the Bash call that asked for it
        subprocess.Popen([sys.executable, __file__, name], env={**os.environ, "CLOSE_SESSION_DETACHED": "1"},
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"{name} closes once this turn ends.")
    else:
        close(name)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
