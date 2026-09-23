#!/usr/bin/env python3
"""Show a session its mission on every prompt, and each agent it launches at the agent's start.

The mission is `$CLAUDE_PLUGIN_DATA/mission/<session id>.md`, written by the
model where `kickoff` names it. No file, no output.
"""
import json
import os
import pathlib
import sys

payload = json.load(sys.stdin)
event = payload["hook_event_name"]
path = pathlib.Path(os.environ["CLAUDE_PLUGIN_DATA"], "mission", payload["session_id"] + ".md")
if path.exists():
    label = "Mission of the session that launched you:\n" if event == "SubagentStart" else "Mission:\n"
    context = label + path.read_text()
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
