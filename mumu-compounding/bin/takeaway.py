#!/usr/bin/env python3
"""Ask for a harvest of lessons before a session stops, in an armed repository.

Two uses:

  takeaway.py              the Stop hook: the hook payload on stdin, the
                           plugin's data directory in CLAUDE_PLUGIN_DATA.
  takeaway.py arm <data>   arm the repository of the current directory; the
                           retro skill passes the plugin's data directory,
                           which a Bash call does not inherit.

The hook blocks once, with PROMPT, only when all four hold; otherwise it exits
0 and says nothing:

  - the repository (its git common dir) is armed: <data>/armed/<key> exists;
  - the session has a person in it: no transcript entry came from `-p`,
    whose entrypoint starts with "sdk";
  - WORK_THRESHOLD or more tool calls since the harvest that this hook's
    last block asked for;
  - HARVEST_INTERVAL or more minutes since this session's last block, or
    no block yet in this session.

WORK_THRESHOLD and HARVEST_INTERVAL can be set from the environment.

Every call counts, since a lesson can come from a read.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

WORK_THRESHOLD = int(os.environ.get("WORK_THRESHOLD", "8"))
HARVEST_INTERVAL = float(os.environ.get("HARVEST_INTERVAL", "30"))
PROMPT = "Before you stop, harvest this session's work with the retro skill."


def repo_key(cwd):
    """The armed-file name for the repository at cwd, or None outside one."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return hashlib.sha256(os.path.realpath(out).encode()).hexdigest()[:16]


def is_previous_block(entry):
    """True for the summary the harness wrote when this hook last blocked."""
    if entry.get("type") != "system" or entry.get("subtype") != "stop_hook_summary":
        return False
    return PROMPT in " ".join(entry.get("hookErrors") or [])


def headless(entries):
    """True when the session was started by `claude -p` or the SDK."""
    return any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries)


def window_start(entries):
    """Index after which tool calls count.

    The window opens at this hook's last block, but the harvest that block
    asked for makes calls too, so it opens only at the next summary: the
    one the harvest's own stop wrote.
    """
    blocked = None
    for i, entry in enumerate(entries):
        if is_previous_block(entry):
            blocked = i
    if blocked is None:
        return 0
    for i in range(blocked + 1, len(entries)):
        if entries[i].get("subtype") == "stop_hook_summary":
            return i + 1
    return len(entries)


def minutes_since_block(entries):
    """Minutes since this hook's last block, or None when it has not blocked."""
    stamps = [e.get("timestamp") for e in entries if is_previous_block(e)]
    if not stamps:
        return None
    try:
        at = datetime.fromisoformat(str(stamps[-1]).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - at).total_seconds() / 60


def work_done(entries):
    """Count the tool calls made in the current window."""
    count = 0
    for entry in entries[window_start(entries):]:
        if entry.get("type") != "assistant":
            continue
        for block in entry["message"]["content"]:
            if block.get("type") == "tool_use":
                count += 1
    return count


def entries_of(path):
    """Every JSON line of a transcript, in order; unreadable lines are skipped."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return parsed


def arm(data):
    key = repo_key(os.getcwd())
    if key is None:
        print(f"not armed: {os.getcwd()} is not inside a git repository", file=sys.stderr)
        return 1
    path = os.path.join(data, "armed", key)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(os.getcwd() + "\n")
    except OSError as error:
        print(f"not armed: {error}", file=sys.stderr)
        return 1
    print(f"armed {os.getcwd()} at {path}")
    return 0


def hook():
    payload = json.load(sys.stdin)
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    key = repo_key(payload.get("cwd") or os.getcwd())
    if not data or key is None or not os.path.exists(os.path.join(data, "armed", key)):
        return 0
    entries = entries_of(payload.get("transcript_path") or "")
    if entries is None or headless(entries):
        return 0
    since = minutes_since_block(entries)
    if since is not None and since < HARVEST_INTERVAL:
        return 0
    if work_done(entries) >= WORK_THRESHOLD:
        json.dump({"decision": "block", "reason": PROMPT}, sys.stdout)
    return 0


def main():
    if sys.argv[1:2] == ["arm"]:
        if len(sys.argv) != 3:
            print("usage: takeaway.py arm <plugin data directory>", file=sys.stderr)
            return 2
        return arm(sys.argv[2])
    return hook()


if __name__ == "__main__":
    sys.exit(main())
