"""A run's stamp file, `<folder>/last-map`, whose age says whether the run is due again, and the dream's run lock,
`<data>/dream.lock`, which the dreaming workflow touches at its start and removes at its end."""
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
    """True when <data>/dream.lock is under LOCK_HOURS old: a dreaming workflow runs on this data now."""
    lock = os.path.join(data, "dream.lock")
    return os.path.exists(lock) and os.path.getmtime(lock) > time.time() - LOCK_HOURS * 3600
