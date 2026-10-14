#!/usr/bin/env python3
"""Timing-bound steps live in this hook, routed per event and role, instead of in the playbooks."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
# only where a command segment starts, so gh text quoted inside another command's argument is not read as a call
GH_TEXT = re.compile(r"(?:^|&&|\|\||[;|\n])\s*(gh (issue|pr) (create|comment|edit)\b)")


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
    command = re.split(r"&&|\|\||[;|\n]", command[GH_TEXT.search(command).start(1):])[0] if GH_TEXT.search(command) else ""
    title = re.search(r"(?<!\S)(--title|-t)[= ](\"[^\"]*\"|'[^']*'|[^\s\"']\S*)", command)
    size = title and len(title.group(2)) - (2 if title.group(2)[0] in "\"'" else 0)
    reason = ("Write the text to a scratch file first, then pass it with --body-file." if re.search(r"(?<!\S)(--body|-b)[= ]", command)
              else f"Title is {size} characters; shorten it to 40, verb first. Nothing in this command ran, so write any body file again." if size and size > 40 else None)
    return reason and {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}}


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
if kind != "PreToolUse" or GH_TEXT.search((event.get("tool_input") or {}).get("command", "")):  # skip other Bash fast
    listed, me = team.sessions(event.get("session_id"))
    name = me.get("name") or ""
    # a name with neither suffix is a session outside any team, such as the owner's own, so it gets no teamwork steps
    role = "manager" if name.endswith("-manager") else "worker" if name.endswith("-worker") else None
    if out := role and route(kind, event, role, me, listed):
        print(json.dumps(out))
