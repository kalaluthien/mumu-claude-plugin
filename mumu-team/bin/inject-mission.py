#!/usr/bin/env python3
"""Show a session its mission on every prompt, and each agent it launches at the agent's start.

The mission is `$CLAUDE_PLUGIN_DATA/mission/<key>.md`, `<key>` being
`team.session_key`, written by the model where `kickoff` names it. It is a
cache of GitHub: missing in a session named `*-lead`, it is rebuilt with
`team.rebuild` and written; present, no `gh` runs. No file and nothing rebuilt,
no output. Each line `team.read_mission` would skip is named in a warning with
the forms it reads.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

payload = json.load(sys.stdin)
event = payload["hook_event_name"]
path = pathlib.Path(os.environ["CLAUDE_PLUGIN_DATA"], "mission", team.session_key(payload["session_id"]) + ".md")
if not path.exists() and path.stem.endswith("-lead"):
    rebuilt = team.rebuild(payload.get("cwd") or os.getcwd())
    if rebuilt:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rebuilt)
if path.exists():
    label = "Mission of the session that launched you" if event == "SubagentStart" else "Mission"
    text = path.read_text()
    context = f"{label} (`{path}`):\n" + text
    bad = team.unrecognised(text)
    if bad:
        context += ("\nWarning: mission lines not recognised, so ignored: " + ", ".join(f"`{line}`" for line in bad)
                    + ". Rewrite each as one of: " + ", ".join(f"`{form}`" for form in team.FORMS)
                    + " (keys in any case, blank lines allowed).\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
