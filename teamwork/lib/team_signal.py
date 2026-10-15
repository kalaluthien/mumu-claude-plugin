"""The file a team session touches when it changes the issues, so a reader of GitHub knows when to read."""
import pathlib

SIGNAL = pathlib.Path.home() / ".claude" / "teamwork" / "issues-changed"


def stamp():
    """When the signal file last changed, in nanoseconds; 0 when it is missing."""
    try:
        return SIGNAL.stat().st_mtime_ns
    except OSError:
        return 0
