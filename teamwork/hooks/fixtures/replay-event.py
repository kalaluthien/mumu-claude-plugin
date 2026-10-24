#!/usr/bin/env python3
"""Replay one Bash event through route-event.py as a worker in a fresh git repo, and print what the hook did: deny, block, warn, other or silent.

usage: replay-event.py <Pre|Post> <settings json, or none for no settings file> <command> [text]
With `text` it prints the hook's message (the deny reason, the block reason and the context) on the lines after the verdict.
A fake herdr names the session t-worker; a fake gh reads every issue back with a body whose holders line sits outside a fence."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

kind, settings, command = sys.argv[1:4]  # sys.argv[4] may be `text`
d = pathlib.Path(tempfile.mkdtemp())
(d / "bin").mkdir()
(d / "repo").mkdir()
for name, out in (("herdr", {"result": {"agents": [{"pane_id": "p1", "name": "t-worker"}]}}), ("gh", {"body": "holders: a"})):
    (d / "bin" / name).write_text(f"#!/bin/sh\necho '{json.dumps(out)}'\n")
    (d / "bin" / name).chmod(0o755)
subprocess.run(["git", "init", "-q", str(d / "repo")], check=True)
if settings != "none":
    (d / "repo" / ".teamwork").mkdir()
    (d / "repo" / ".teamwork" / "settings.json").write_text(settings)
event = {"hook_event_name": kind + "ToolUse", "cwd": str(d / "repo"), "tool_input": {"command": command},
         "tool_response": "https://github.com/o/r/issues/5"}
env = {**os.environ, "PATH": f"{d / 'bin'}:{os.environ['PATH']}", "HERDR_PANE_ID": "p1"}
out = subprocess.run([str(pathlib.Path(__file__).resolve().parents[1] / "route-event.py")], input=json.dumps(event), capture_output=True, text=True, env=env).stdout
got = json.loads(out) if out.strip() else {}
hook = got.get("hookSpecificOutput", {})
print("block" if got.get("decision") == "block" else "deny" if hook.get("permissionDecision") == "deny"
      else "warn" if str(hook.get("additionalContext", "")).startswith("Warning:") else "other" if got else "silent")
if sys.argv[4:5] == ["text"]:
    print(*[m for m in (hook.get("permissionDecisionReason"), got.get("reason"), hook.get("additionalContext")) if m], sep="\n")
