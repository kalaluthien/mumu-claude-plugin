"""Runs a command and parses its JSON output, and names the install page of a command that is missing."""
import json
import shutil
import subprocess

INSTALL = {"gh": "https://cli.github.com", "herdr": "https://herdr.dev"}


def run(*argv):
    """The command's parsed JSON output, or None when it fails or is missing, such as a tool outside the host it needs."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True)
        return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, ValueError):
        return None


def missing(name):
    """The line that tells a person to install NAME when it is not on PATH, else None."""
    return None if shutil.which(name) else f"`{name}` is not installed: install it from {INSTALL[name]}"


def need(name):
    """Stops with the install line when NAME is missing, so a person reads the fix instead of a traceback."""
    if line := missing(name):
        raise SystemExit(line)
