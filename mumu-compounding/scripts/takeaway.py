#!/usr/bin/env python3
"""Ask for a harvest of lessons, or a dream, before a session stops, in an armed repository.

  takeaway.py              the Stop hook: its payload on stdin, the plugin's
                           data directory in CLAUDE_PLUGIN_DATA
  takeaway.py arm <data>   arm the current directory's repository; a Bash
                           call does not inherit CLAUDE_PLUGIN_DATA

The hook blocks with PROMPT only when the repository (its git common dir) is
armed, no transcript entry came from `claude -p` or the SDK, WORK_THRESHOLD
tool calls of any kind were made since the harvest its last block asked for,
and HARVEST_INTERVAL minutes passed since that block; else it exits silently.
So it asks once at 40 calls in a session, then again only after 40 more calls
and 120 min. Failures, refusals or pushback as a trigger reached few sessions
beyond it that later wrote a memory (replay-harvest-triggers.py, #217).

At a stop that asks no harvest, it blocks with DREAM_PROMPT once
DREAM_THRESHOLD memory files of the transcript's projects folder changed since
<data>/dreamed, touching that stamp when it asks and when the transcript shows
dream ran after it, so it asks again only once as many files change anew.
Changed memory files beat shell defects and elapsed days as the trigger
(replay-dream-triggers.py, #204).
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

WORK_THRESHOLD = int(os.environ.get("WORK_THRESHOLD", "40"))
HARVEST_INTERVAL = float(os.environ.get("HARVEST_INTERVAL", "120"))
DREAM_THRESHOLD = int(os.environ.get("DREAM_THRESHOLD", "5"))
PROMPT = "Before you stop, harvest this session's work with the retro skill."
DREAM_PROMPT = "Memory files changed since the last dream: run the dream skill before you stop."


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


def seconds(entry):
    try:
        return datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def minutes_since_block(entries):
    at = seconds(entries[blocks(entries)[-1]]) if blocks(entries) else None
    return None if at is None else (datetime.now(timezone.utc).timestamp() - at) / 60


def dream_ran(entries, since):
    """Whether dream ran, typed or by the Skill tool, after since."""
    for entry in entries:
        body = (entry.get("message") or {}).get("content")
        text = body if isinstance(body, str) else json.dumps(body)
        if (seconds(entry) or 0) > since and (
                re.search(r"<command-name>/(mumu-compounding:)?dream</command-name>", text)
                or re.search(r'"skill": "(mumu-compounding:)?dream"', text)):
            return True
    return False


def memory_changed(projects, since):
    """Memory files, index aside, changed after since."""
    return sum(1 for path in glob.glob(os.path.join(glob.escape(projects), "*", "memory", "*.md"))
               if os.path.basename(path) != "MEMORY.md" and os.path.getmtime(path) > since)


def dream(data, transcript, entries):
    """Whether to ask for a dream; touches the stamp when it asks or dream ran."""
    stamp = os.path.join(data, "dreamed")
    if not os.path.exists(stamp):
        open(stamp, "w").close()
        return False
    since = os.path.getmtime(stamp)
    ask = memory_changed(os.path.dirname(os.path.dirname(transcript)), since) >= DREAM_THRESHOLD
    ran = dream_ran(entries, since)
    if ask or ran:
        os.utime(stamp)
    return ask and not ran


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
    elif dream(data, payload.get("transcript_path"), entries):
        json.dump({"decision": "block", "reason": DREAM_PROMPT}, sys.stdout)
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["arm"]:
        if len(sys.argv) == 3:
            sys.exit(arm(sys.argv[2]))
        print("usage: takeaway.py arm <plugin data directory>", file=sys.stderr)
        sys.exit(2)
    sys.exit(hook())
