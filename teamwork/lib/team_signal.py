"""The file a team session touches when it changes the tasks, so a reader of the board knows when to read."""
import claude_config

SIGNAL = claude_config.folder() / "teamwork" / "tasks-changed"
OLD_SIGNAL = SIGNAL.with_name("issues-changed")  # what a heartbeat started before the rename waits on


def touch():
    """Marks a change to the tasks, which the task pane and the heartbeat wait on."""
    SIGNAL.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL.touch()
    OLD_SIGNAL.touch()


def stamp():
    """When either signal file last changed, in nanoseconds; 0 when both are missing."""
    times = [0]
    for signal in (SIGNAL, OLD_SIGNAL):
        try:
            times.append(signal.stat().st_mtime_ns)
        except OSError:
            pass
    return max(times)
