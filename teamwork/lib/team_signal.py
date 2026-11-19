"""The file a team session touches when it changes the tasks, so a reader of the board knows when to read."""
import claude_config

SIGNAL = claude_config.folder() / "teamwork" / "tasks-changed"


def touch():
    """Marks a change to the tasks, which the task pane and the heartbeat wait on."""
    SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL.touch()


def stamp():
    """When the signal file last changed, in nanoseconds; 0 when it is missing."""
    try:
        return SIGNAL.stat().st_mtime_ns
    except OSError:
        return 0
