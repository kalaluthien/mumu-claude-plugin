#!/usr/bin/env python3
"""Ask for a harvest of lessons before a session stops, in an armed repository.

  takeaway.py              the Stop hook: its payload on stdin, the plugin's
                           data directory in CLAUDE_PLUGIN_DATA
  takeaway.py arm <data>   arm the current directory's repository; a Bash
                           call does not inherit CLAUDE_PLUGIN_DATA

The hook blocks with PROMPT only when the repository (its git common dir) is
armed, no transcript entry came from `claude -p` or the SDK, WORK_THRESHOLD
tool calls of any kind were made since the harvest its last block asked for,
and HARVEST_INTERVAL minutes passed since that block; else it exits silently.
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
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return hashlib.sha256(os.path.realpath(out).encode()).hexdigest()[:16]


def is_block(entry):
    return (entry.get("type"), entry.get("subtype")) == ("system", "stop_hook_summary") and PROMPT in " ".join(entry.get("hookErrors") or [])


def blocks(entries):
    return [i for i, e in enumerate(entries) if is_block(e)]


def work_done(entries):
    """Tool calls after the stop that ended the harvest the last block asked for."""
    start = 0
    if blocks(entries):
        later = [i for i in range(blocks(entries)[-1] + 1, len(entries))
                 if entries[i].get("subtype") == "stop_hook_summary"]
        start = later[0] + 1 if later else len(entries)
    return sum(1 for e in entries[start:] if e.get("type") == "assistant"
               for block in e["message"]["content"] if block.get("type") == "tool_use")


def minutes_since_block(entries):
    try:
        at = datetime.fromisoformat(str(entries[blocks(entries)[-1]].get("timestamp")).replace("Z", "+00:00"))
    except (IndexError, ValueError):
        return None
    return (datetime.now(timezone.utc) - at).total_seconds() / 60


def entries_of(path):
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


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
    if entries is None or any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
        return 0
    since = minutes_since_block(entries)
    if (since is None or since >= HARVEST_INTERVAL) and work_done(entries) >= WORK_THRESHOLD:
        json.dump({"decision": "block", "reason": PROMPT}, sys.stdout)
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["arm"]:
        if len(sys.argv) == 3:
            sys.exit(arm(sys.argv[2]))
        print("usage: takeaway.py arm <plugin data directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(hook())
