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


def start(name, role, me, listed):
    gaps = team.manager_actions(me, listed) if role == "manager" else team.worker_goal(me)
    text = f"You are {name}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}."
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join([text, *gaps])}}


def stop(event, me):
    goal = [g for g in team.worker_goal(me) if g.endswith(": open")]
    if goal and not event.get("stop_hook_active"):  # once per stop, so a real wait still ends the turn
        return {"decision": "block", "reason": "Your goal still waits on you:\n" + "\n".join(goal) + "\nTake its next step;"
                " stop again only while a subagent, a check or your manager has it."}


def gh_text(command):
    title = re.search(r"(--title|-t)[= ](\"[^\"]*\"|'[^']*')", command)
    if re.search(r"(--body|-b)[= ]", command):
        reason = "Write the text to a scratch file first, then pass it with --body-file."
    elif title and len(title.group(2)) - 2 > 40:
        reason = "Shorten the title to 40 characters, verb first."
    else:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main():
    event = json.load(sys.stdin)
    kind, command = event.get("hook_event_name"), (event.get("tool_input") or {}).get("command", "")
    if kind == "PreToolUse" and not GH_TEXT.search(command):
        return  # most Bash calls: answered before asking herdr anything
    listed, me = team.sessions()
    name = me.get("name") or ""
    role = "manager" if name.endswith("-manager") else "worker" if name.endswith("-worker") else None
    if not role:
        return
    out = (start(name, role, me, listed) if kind == "SessionStart" else gh_text(command) if kind == "PreToolUse"
           else stop(event, me) if kind == "Stop" and role == "worker" else None)
    if out:
        print(json.dumps(out))


main()
