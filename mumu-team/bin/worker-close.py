#!/usr/bin/env python3
"""Close a worker in one call: its Claude session, its exit dialogs and its tab.

usage: worker-close.py <name>

Sends `/exit` to the agent herdr lists as `<name>`, and answers each exit dialog
in `DIALOGS` at most once, by the key its row names: the background-work dialog
exits, and a pending feedback draft is discarded, never sent, since sending is
the owner's to decide. It then waits until herdr no longer lists the agent, closes every tab labelled
`<name>`. An agent already gone skips to the tab. Prints
`closed <name>`. `WORKER_CLOSE_TIMEOUT` (60) and `WORKER_CLOSE_POLL` (1) are seconds.
The keys go through `herdr agent send-keys`, so auto mode needs the allow rule
`Bash(herdr agent send-keys *)`.
"""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402

# (screen text, key) per exit dialog, as Claude Code v2.1.282 shows it (issue #79).
DIALOGS = [
    ("Background work is running", "enter"),  # first option: Exit
    ("unsent feedback draft", "esc"),  # Esc to discard and exit
    ("d to discard", "d"),  # the drafts list or one draft's review, reached by Enter
    ("No feedback drafts queued", "esc"),  # the empty panel after `d`
]


def pane(name):
    """The pane of the agent herdr lists as `name`, or None."""
    a = herdr.agent(name)
    return a and a["pane_id"]


def exit_session(name, timeout, poll):
    """`/exit` the agent `name`, answering each dialog in `DIALOGS` at most once, and return once herdr no longer lists it."""
    target = pane(name)
    if target is None:
        return
    herdr.prompt(target, "/exit")
    answered, deadline = set(), time.time() + timeout
    while pane(name) is not None:
        if time.time() >= deadline:
            raise RuntimeError(f"{name} still running after {timeout:g}s; see `herdr agent read {target}`")
        screen = herdr.screen(target)
        for text, key in DIALOGS:
            if text in screen and text not in answered:
                herdr.keys(target, key)
                answered.add(text)
                break
        time.sleep(poll)


def main(argv):
    if len(argv) != 1:
        print("usage: worker-close.py <name>", file=sys.stderr)
        return 2
    name = argv[0]
    timeout, poll = float(os.environ.get("WORKER_CLOSE_TIMEOUT", 60)), float(os.environ.get("WORKER_CLOSE_POLL", 1))
    try:
        exit_session(name, timeout, poll)
        for tab in herdr.tabs():
            if tab.get("label") == name:
                herdr.close_tab(tab["tab_id"])
    except RuntimeError as e:
        print(f"worker-close.py: {e}", file=sys.stderr)
        return 1
    print(f"closed {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
