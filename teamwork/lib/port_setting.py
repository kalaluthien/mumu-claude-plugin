"""A port's adapter name: its environment variable, else that variable in the `env` of the project's Claude settings, read again at each call,
so a process started before the setting was written, such as the heartbeat, follows it."""
import functools
import json
import os
import pathlib

import data_folder
import team_settings

FILES = (pathlib.Path(".claude", "settings.local.json"), pathlib.Path(".claude", "settings.json"))  # the local file wins, as in Claude Code


@functools.cache
def roots():
    """The current folder's git root, then the main checkout's, since a worktree has no `settings.local.json` of its own."""
    common = data_folder.common_folder()
    found = [team_settings.root(os.getcwd()), common.parent if common and common.name == ".git" else None]
    return list(dict.fromkeys(candidate for candidate in found if candidate))


def value(variable, default):
    """VARIABLE from the environment, else from the first settings file that sets it, else DEFAULT."""
    if os.environ.get(variable):
        return os.environ[variable]
    for path in (root / file for root in roots() for file in FILES):
        try:
            env = json.loads(path.read_text()).get("env")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(env, dict) and isinstance(env.get(variable), str) and env[variable]:
            return env[variable]
    return default
