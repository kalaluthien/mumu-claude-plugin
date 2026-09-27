#!/usr/bin/env python3
"""Close a worker: `/exit` its session, answering each exit dialog, and close every tab labelled `<name>`.

`--pane <pane>`, which `lead-start.py --replace` runs detached, closes the session in that pane instead, named or not:
once its turn ends, it exits it the same way and closes its tab by id."""
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


def exit_session(key, timeout, poll, field="name"):
    """`/exit` the agent whose `field` is `key`, answering each dialog in `DIALOGS` at most once, and return once herdr no longer lists it."""
    agent = herdr.agent(key, field) or {}
    target = agent.get("pane_id")
    if target is None:
        return
    if agent.get("agent_status") != "blocked":  # blocked: a dialog is already up, and herdr refuses a prompt with `agent_blocked`
        herdr.prompt(target, "/exit")
    answered, deadline = set(), time.time() + timeout
    while herdr.agent(key, field):
        if time.time() >= deadline:
            raise RuntimeError(f"{key} still running after {timeout:g}s; see `herdr agent read {target}`")
        screen = herdr.screen(target)
        for text, key_ in DIALOGS:
            if text in screen and text not in answered:
                herdr.keys(target, key_)
                answered.add(text)
                break
        time.sleep(poll)


def close_pane(pane, timeout, poll, idle_timeout):
    """Once the agent in `pane` ends its turn, exit it and close its tab by id, whatever the tab's label."""
    deadline = time.time() + idle_timeout
    while (agent := herdr.agent(pane, "pane_id")) and agent.get("agent_status") not in ("idle", "done"):
        if time.time() >= deadline:
            raise RuntimeError(f"{pane} still at work after {idle_timeout:g}s")
        time.sleep(poll)
    if agent:
        exit_session(pane, timeout, poll, "pane_id")
        herdr.close_tab(agent["tab_id"])


def main(argv):
    if len(argv) != (2 if argv[:1] == ["--pane"] else 1) or argv[-1].startswith("-"):
        print("usage: worker-close.py <name> | --pane <pane>", file=sys.stderr)
        return 2
    name = argv[-1]
    timeout, poll = float(os.environ.get("WORKER_CLOSE_TIMEOUT", 60)), float(os.environ.get("WORKER_CLOSE_POLL", 1))
    try:
        if argv[0] == "--pane":
            close_pane(name, timeout, poll, float(os.environ.get("WORKER_CLOSE_IDLE_TIMEOUT", 3600)))
        else:
            exit_session(name, timeout, poll)
            for tab in herdr.listed("tab"):
                if tab.get("label") == name:
                    herdr.close_tab(tab["tab_id"])
    except RuntimeError as e:
        sys.exit(f"worker-close.py: {e}")
    print(f"closed {name}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
