"""The ISO time the board and the changes stamp their records with."""
from datetime import datetime, timezone


def stamp(seconds=None):
    """SECONDS since the epoch, else now, as `2026-11-04T04:00:00Z`."""
    return datetime.fromtimestamp(seconds or datetime.now().timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
