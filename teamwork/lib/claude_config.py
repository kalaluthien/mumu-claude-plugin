"""The Claude config folder, which Claude Code moves to CLAUDE_CONFIG_DIR when that is set."""
import os
import pathlib


def folder():
    """The Claude config folder: CLAUDE_CONFIG_DIR, else ~/.claude."""
    return pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")
