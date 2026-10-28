"""Runs a command and parses its JSON output."""
import json
import subprocess


def run(*argv):
    """The command's parsed JSON output, or None when it fails or is missing, such as a tool outside the host it needs."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True)
        return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, ValueError):
        return None

