"""The file a team session touches when it changes the tasks or the changes of its repository, kept in that repository's git common folder,
so a reader of one repository's board knows when to read and a write in another wakes none of its readers."""
import functools

import data_folder


@functools.lru_cache(maxsize=None)
def signal():
    """The signal file of the current folder's repository, found once, since a process stays in one repository; None outside one."""
    common = data_folder.common_folder()
    return common and common / "teamwork-tasks-changed"


def touch():
    """Marks a change, which the task pane and the heartbeat wait on; nothing outside a repository, which has no reader to wake."""
    path = signal()
    if path is not None:
        path.touch()


def stamp():
    """When the signal file last changed, in nanoseconds; 0 when it is missing or outside a repository."""
    try:
        return signal().stat().st_mtime_ns
    except (AttributeError, OSError):
        return 0
