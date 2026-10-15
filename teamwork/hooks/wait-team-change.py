#!/usr/bin/env python3
"""usage: wait-team-change.py

Print `changed` once at start, then once each time a team session marks a change to the issues, until killed.
It blocks on the signal file through kqueue, so it reads GitHub never and wakes only when a session touches the file."""
import pathlib
import select

SIGNAL = pathlib.Path.home() / ".claude" / "teamwork" / "issues-changed"
EVENTS = select.KQ_NOTE_WRITE | select.KQ_NOTE_ATTRIB | select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME


def watch(queue):
    """A watch on the signal file, made anew when it is missing, since a deleted file's watch never fires again."""
    SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL.touch()
    handle = open(SIGNAL)
    queue.control([select.kevent(handle, select.KQ_FILTER_VNODE, select.KQ_EV_ADD | select.KQ_EV_CLEAR, EVENTS)], 0)
    return handle


queue = select.kqueue()
handle = watch(queue)
print("changed", flush=True)
while True:
    for event in queue.control(None, 1):
        if event.fflags & (select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME):
            handle.close()
            handle = watch(queue)
        print("changed", flush=True)
