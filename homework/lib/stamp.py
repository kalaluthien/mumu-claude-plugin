"""A run's stamp file, `<folder>/last-map`, whose age says whether the run is due again, and the dream's run lock,
`<data>/dream.lock`, which the session about to run the dreaming workflow takes and the workflow removes at its end."""
import fcntl
import os
import time

HOURS = {"dejavu": 24, "habit": 168}
LOCK_HOURS = 6  # longer than any dream run, so a lock a failed run left stops holding


def due(folder, hours=None):
    """True when <folder>/last-map is missing or at least <hours> old, <hours> by the folder's name when not given."""
    if hours is None:
        hours = HOURS.get(os.path.basename(os.path.normpath(folder)), HOURS["dejavu"])
    stamp = os.path.join(folder, "last-map")
    return not os.path.exists(stamp) or os.path.getmtime(stamp) <= time.time() - hours * 3600


def running(data):
    """True when <data>/dream.lock was written under LOCK_HOURS ago, a future time counted as far: a dreaming workflow
    runs on this data now."""
    lock = os.path.join(data, "dream.lock")
    return os.path.exists(lock) and abs(time.time() - os.path.getmtime(lock)) < LOCK_HOURS * 3600


def lock(data):
    """Take <data>/dream.lock unless a fresh one holds; True when taken, by one caller only when several race."""
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, "dream.lock.guard"), "w") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)  # one caller at a time checks, clears a stale lock and takes it
        if running(data):
            return False
        with open(os.path.join(data, "dream.lock"), "w"):
            return True
