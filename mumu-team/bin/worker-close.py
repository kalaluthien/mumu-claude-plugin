#!/usr/bin/env python3
"""Close a worker: `/exit` its session, answering each exit dialog, and close every tab labelled `<name>`."""
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


def exit_session(name, timeout, poll):
    """`/exit` the agent `name`, answering each dialog in `DIALOGS` at most once, and return once herdr no longer lists it."""
    target = (herdr.agent(name) or {}).get("pane_id")
    if target is None:
        return
    herdr.prompt(target, "/exit")
    answered, deadline = set(), time.time() + timeout
    while herdr.agent(name):
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
        for tab in herdr.listed("tab"):
            if tab.get("label") == name:
                herdr.close_tab(tab["tab_id"])
    except RuntimeError as e:
        sys.exit(f"worker-close.py: {e}")
    print(f"closed {name}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
