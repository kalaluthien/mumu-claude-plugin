#!/usr/bin/env python3
"""usage: wait-team-change.py

Print `changed` once at start, then once per burst of marks by team sessions to the issues, after the file has been quiet for QUIET seconds, until killed.
It blocks on the signal file through kqueue, so it reads GitHub never and wakes only when a session touches the file."""
import pathlib
import select
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
from team_signal import SIGNAL  # noqa: E402

QUIET = 2  # seconds without a mark that end a burst
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
    # one `changed` per burst: a session often marks several writes in a row, and each would otherwise read the board
    event = queue.control(None, 1)
    while event:
        if event[0].fflags & (select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME):
            handle.close()
            handle = watch(queue)
        event = queue.control(None, 1, QUIET)
    print("changed", flush=True)
