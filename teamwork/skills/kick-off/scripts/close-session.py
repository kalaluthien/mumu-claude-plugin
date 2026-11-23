#!/usr/bin/env python3
"""Close a named session once it stops working: send it its exit, answer the dialogs it shows, then close its tab.

usage: close-session.py <name> [--force]

Another session's close is refused, exit 2, while a task it holds has an open `BLOCKED:` no `DECIDED:` answered, printing that task's url and question,
since its worker waits on that answer; `--force` closes it anyway. A session closing itself runs detached, so it closes once the turn ends. TEAMWORK_CLOSE_SESSION_TIMEOUT (default 3600) bounds the
wait in seconds."""
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import agent  # noqa: E402
import board  # noqa: E402
import session  # noqa: E402
import task_state  # noqa: E402

TIMEOUT, POLL = float(os.environ.get("TEAMWORK_CLOSE_SESSION_TIMEOUT", 3600)), 1.0


def close(name):
    deadline = time.time() + TIMEOUT
    while (listed := session.agent(name)) and listed.get("agent_status") == "working":
        if time.time() >= deadline:
            sys.exit(f"close-session.py: {name} still at work after {TIMEOUT:g}s; nothing closed.")
        time.sleep(POLL)
    if not listed:
        return print(f"{name} is not live; nothing to close.")
    if listed.get("agent_status") != "blocked":  # a blocked session already shows a dialog and refuses a prompt
        session.prompt(name, agent.EXIT)  # the name, which herdr resolves on each call, since it may move the pane
    answered = set()
    while (now := session.agent(name)) and time.time() < deadline:
        listed, screen = now, session.screen(name)  # the latest read, whose tab close shuts
        for text, key in agent.DIALOGS:
            if text in screen and text not in answered:
                session.send_keys(name, key)
                answered.add(text)
                break
        time.sleep(POLL)
    if session.agent(name):
        sys.exit(f"close-session.py: {name} is still live after {TIMEOUT:g}s; its tab stays open.")
    closed = session.close(listed)
    print(f"{name} exited and its {closed} closed." if closed else f"{name} exited; its pane was already closed, so nothing more closed.")


def waiting(name):
    """Each open question on an open task whose recorded holders name NAME, as (task url, question line); none when the board cannot be read."""
    try:
        found = board.tasks("open") or []
    except LookupError:  # outside a repository there is no board to read
        return []
    return [(task.get("url", f"#{task['number']}"), task_state.first_line(question["ask"]["body"]))
            for task in found if name in ((task_state.holder_values(task) or [[]])[-1])
            for question in task_state.open_questions(task)]


def main(args):
    force = "--force" in args
    args = [arg for arg in args if arg != "--force"]
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    name = args[0]
    own = session.own_name() == name
    if not own and not force and (asked := waiting(name)):
        for url, question in asked:
            print(f"{url} {question}")
        print(f"close-session.py: {name} waits on {len(asked)} open question(s) above; answer each by `decide --answers <url>`, or pass --force; nothing closed.", file=sys.stderr)
        return 2
    if own and not os.environ.get("TEAMWORK_CLOSE_SESSION_DETACHED"):  # detached, so it outlives the Bash call that asked for it
        subprocess.Popen([sys.executable, __file__, name], env={**os.environ, "TEAMWORK_CLOSE_SESSION_DETACHED": "1"},
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"{name} closes once this turn ends.")
    else:
        close(name)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
