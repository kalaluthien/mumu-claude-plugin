#!/usr/bin/env python3
"""UserPromptSubmit hook: tell the session to re-read each kickoff references file changed since it last read it.

A read is a `Read` of the file, or a `Bash` command naming this plugin's root and
the file's name; a change is an mtime after the newest read.
"""
import datetime
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFS = ROOT / "skills" / "kickoff" / "references"
# The root as a command may spell it: resolved, or through a symlink such as macOS's /var or /tmp.
ROOTS = {str(ROOT), os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.environ.get("CLAUDE_PLUGIN_ROOT") or str(ROOT)}


def uses(transcript):
    """Each tool call of the transcript, as (epoch seconds, tool name, input)."""
    with open(transcript) as f:
        for line in f:
            if '"tool_use"' not in line:
                continue
            try:
                entry = json.loads(line)
                stamp = datetime.datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).timestamp()
                content = entry["message"]["content"]
            except (ValueError, KeyError, TypeError):
                continue
            for c in content if isinstance(content, list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    yield stamp, c.get("name"), c.get("input") or {}


def reads(name, tool, given, ref):
    """Whether one tool call reads `ref`."""
    if tool == "Read":
        path = given.get("file_path") or ""
        return bool(path) and pathlib.Path(path).resolve() == ref.resolve()
    if tool == "Bash":
        command = given.get("command") or ""
        return any(root in command for root in ROOTS) and re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w.-])", command) is not None
    return False


def changed(transcript):
    """The references files read in `transcript` and changed since their newest read."""
    refs = sorted(REFS.glob("*.md"))
    last = {}
    for stamp, tool, given in uses(transcript):
        for ref in refs:
            if reads(ref.name, tool, given, ref):
                last[ref] = max(last.get(ref, 0), stamp)
    return [ref for ref in refs if ref in last and ref.stat().st_mtime > last[ref]]


def main():
    try:
        stale = changed(json.load(sys.stdin)["transcript_path"])
    except (OSError, ValueError, KeyError, TypeError):
        return
    if stale:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "These rules files changed since you last read them; read each again before you act on "
                                 "this prompt: " + ", ".join(str(r) for r in stale),
        }}))


main()
