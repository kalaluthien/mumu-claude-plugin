#!/usr/bin/env python3
"""Timing-bound steps live in this hook, routed per event and role, instead of in the playbooks."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import background_work  # noqa: E402
import herdr_agents  # noqa: E402
import team_gaps  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
EDIT_BODY = PLAYBOOKS.parent / "scripts" / "edit-issue-body.py"
# only where a command segment starts, so gh text quoted inside another command's argument is not read as a call
GH_TEXT = re.compile(r"(?:^|&&|\|\||[;|(`\n]|\b(?:then|do|else)\s)\s*(?:\w+=\S*\s+)*(gh (issue|pr) (create|comment|edit)\b)")
SEGMENT_END = re.compile(r"&&|\|\||[;|)`]|(?<!\\)\n")  # a backslash-newline continues the command


def route(kind, event, role, me, listed):
    command = (event.get("tool_input") or {}).get("command", "")
    if kind == "SessionStart":
        gaps = (team_gaps.manager_actions(me, listed) if role == "manager" else team_gaps.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    # once, so a real wait still stops; never while a subagent or a background command it waits on still runs
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active") and not background_work.running_work(event.get("transcript_path") or ""):
        goal = [g for g in team_gaps.worker_goal(me) if g.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    command = SEGMENT_END.split(command[GH_TEXT.search(command).start(1):])[0] if GH_TEXT.search(command) else ""
    title = re.search(r"(?<!\S)(--title|-t)[= ](\"[^\"]*\"|'[^']*'|[^\s\"']\S*)", command)
    size = title and len(title.group(2)) - (2 if title.group(2)[0] in "\"'" else 0)
    reason = (f"An issue body changes only by {EDIT_BODY} <issue> <diff-file> \"DECIDED: <why>\", which posts the diff as a comment first, as {GRAMMAR} says." if re.match(r"gh issue edit\b", command)
              and re.search(r"(?<!\S)(--body-file|-F|--body|-b)[= ]", command)
              else "Write the text to a scratch file first, then pass it with --body-file." if re.search(r"(?<!\S)(--body|-b)[= ]", command)
              else f"Title is {size} characters; shorten it to 40, verb first. Nothing in this command ran, so write any body file again." if size and size > 40 else None)
    return reason and {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}}


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
if kind != "PreToolUse" or GH_TEXT.search((event.get("tool_input") or {}).get("command", "")):  # skip other Bash fast
    listed, me = herdr_agents.sessions(event.get("session_id"))
    role = herdr_agents.role(me.get("name"))
    if out := role and route(kind, event, role, me, listed):
        print(json.dumps(out))
