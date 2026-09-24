#!/usr/bin/env python3
"""Show a session its mission on every prompt, and each agent it launches at the agent's start.

The mission is `$CLAUDE_PLUGIN_DATA/mission/<session id>.md`, written by the
model where `kickoff` names it. No file, no output. Each line
`team.read_mission` would skip is named in a warning with the forms it reads.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

payload = json.load(sys.stdin)
event = payload["hook_event_name"]
path = pathlib.Path(os.environ["CLAUDE_PLUGIN_DATA"], "mission", payload["session_id"] + ".md")
if path.exists():
    label = "Mission of the session that launched you:\n" if event == "SubagentStart" else "Mission:\n"
    text = path.read_text()
    context = label + text
    bad = team.unrecognised(text)
    if bad:
        context += ("\nWarning: mission lines not recognised, so ignored: " + ", ".join(f"`{line}`" for line in bad)
                    + ". Rewrite each as one of: " + ", ".join(f"`{form}`" for form in team.FORMS)
                    + " (keys in any case, blank lines allowed).\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
