#!/usr/bin/env python3
"""The `route-event` hook: on each event, gather what a teamwork session needs then and route it a line, so timing-bound
steps live here instead of in the playbooks. Silent in a session not named `-manager` or `-worker`."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
GH_TEXT = re.compile(r"\bgh (issue|pr) (create|comment|edit)\b")


def route(kind, event, role, me, listed):
    command = (event.get("tool_input") or {}).get("command", "")
    if kind == "SessionStart":
        gaps = (team.manager_actions(me, listed) if role == "manager" else team.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active"):  # once, so a real wait still stops
        goal = [g for g in team.worker_goal(me) if g.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    command = re.split(r"&&|\|\||;|\|", command[GH_TEXT.search(command).start():])[0] if GH_TEXT.search(command) else ""
    title = re.search(r"(?<!\S)(--title|-t)[= ](\"[^\"]*\"|'[^']*')", command)
    reason = ("Write the text to a scratch file first, then pass it with --body-file." if re.search(r"(?<!\S)(--body|-b)[= ]", command)
              else "Shorten the title to 40 characters, verb first." if title and len(title.group(2)) > 42 else None)
    return reason and {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}}


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
if kind != "PreToolUse" or GH_TEXT.search((event.get("tool_input") or {}).get("command", "")):  # skip other Bash fast
    listed, me = team.sessions(event.get("session_id"))
    name = me.get("name") or ""
    role = "manager" if name.endswith("-manager") else "worker" if name.endswith("-worker") else None
    out = role and route(kind, event, role, me, listed)
    if out:
        print(json.dumps(out))
