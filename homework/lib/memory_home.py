"""The auto-memory home `autoMemoryDirectory` sets, the folder of a repository under it, and every memory folder a shell can find."""
import glob
import json
import os
import pathlib
import subprocess

import claude_config


def git(cwd, *args):
    """A git command's stripped output at cwd, empty when it fails."""
    try:
        result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def checkout(cwd):
    """The main checkout's root of the repository at cwd, which its worktrees share, else cwd itself."""
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return pathlib.Path(common).parent if common else pathlib.Path(cwd).resolve()


def repository(cwd):
    """The repository's name: the last part of its origin's url, else its main checkout's folder name."""
    url = git(cwd, "remote", "get-url", "origin")
    if url:
        return url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1].removesuffix(".git")
    return checkout(cwd).name


def setting(path):
    """The `autoMemoryDirectory` a settings file sets, None when it sets none or cannot be read."""
    try:
        value = json.loads(pathlib.Path(path).read_text()).get("autoMemoryDirectory")
        # a `~user/` of no such user raises RuntimeError
        return pathlib.Path(value).expanduser() if isinstance(value, str) and value else None
    except (OSError, ValueError, AttributeError, RuntimeError):
        return None


def home(cwd=None, config=None):
    """The folder `autoMemoryDirectory` names: the main checkout's local settings first, which Claude Code reads in each worktree too, then the user's; None when unset."""
    config = pathlib.Path(config) if config else claude_config.folder()
    local = [checkout(cwd) / ".claude" / "settings.local.json"] if cwd else []
    for path in [*local, config / "settings.json"]:
        found = setting(path)
        if found:
            return found
    return None


def pools(config=None, cwd="."):
    """Every memory folder: the home the session at cwd reads and each folder under it, then each `<config>/projects/*/memory` that is no link into the home."""
    config = pathlib.Path(config) if config else claude_config.folder()
    root = home(cwd, config)
    found = []
    if root and root.is_dir():
        found = [str(root)] + sorted(str(path) for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))
    for pool in sorted(glob.glob(os.path.join(glob.escape(str(config)), "projects", "*", "memory"))):
        if not os.path.islink(pool):
            found.append(pool)
    return found
