#!/usr/bin/env python3
"""Timing-bound steps live in this hook, routed per event and role, instead of in the playbooks."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import background_work  # noqa: E402
import board  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
EDIT_BODY = PLAYBOOKS.parent / "scripts" / "edit-issue-body.py"
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
REMINDED = {"file": ("`file`", "40 characters"), "change": ("40 characters",), "comment": ("**Comment**", "`comment`"), "change comment": ("**Comment**",),
            "resolve": ("`resolve`",), "edit": ("edit-issue-body", "40 characters"), "change edit": ("40 characters",)}
FENCE = re.compile(r"^```teamwork\n.*?^```", re.S | re.M)
STATE_LINE = re.compile(r"^\s*(holders|deferred):", re.M)


def stray_state(call, cwd):
    """A holders or deferred line in the posted file that no teamwork fence holds, which code never reads."""
    path = call["body file"] and pathlib.Path(cwd or ".") / call["body file"]
    try:
        return bool(path and STATE_LINE.search(FENCE.sub("", path.read_text())))
    except OSError:
        return False


def stray_posted(output):
    """The url the write printed when a holders or deferred line in what it posted sits outside a teamwork fence, read back from the board."""
    url, body = board.posted(output) or (None, "")
    return STATE_LINE.search(FENCE.sub("", body)) and url


def reminder(call, role, cwd):
    called, needles = call["called"], REMINDED.get(call["write"], ())
    found = [f"- {path.relative_to(PLAYBOOKS.parents[1])}:{number}: {line.strip()}"
             for path in (PLAYBOOKS / "protocol.md", PLAYBOOKS / f"{role}.md", GRAMMAR, *sorted((PLAYBOOKS / "adapters").glob("*-github.md")))  # a gh command keeps GitHub's adapter rules, never another board's
             for number, line in enumerate(path.read_text().splitlines(), 1) if any(n in line for n in needles)]
    stray = ["- A `holders:` or `deferred:` line sits outside a ```teamwork fence in the posted file, so code reads no holder: put it inside the fence, as "
             f"{GRAMMAR.relative_to(PLAYBOOKS.parents[1])} says."] if called and stray_state(call, cwd) else []
    return (found or stray) and "\n".join([f"Reminder: the playbook rules this `{called}` must keep:", *found, *stray])


def route(kind, event, role, me, listed):
    call = board.command((event.get("tool_input") or {}).get("command", ""))
    if kind == "PostToolUse":
        stray = call and call["write"] in ("file", "comment", "edit") and stray_posted(json.dumps(event.get("tool_response")))
        return stray and {"decision": "block", "reason": f"A `holders:` or `deferred:` line sits outside a ```teamwork fence in {stray}, so code reads no holder; "
                          f"post the record again with the line inside the fence, as {GRAMMAR} says."}
    if kind == "SessionStart":
        gaps = (team_gaps.manager_actions(me, listed) if role == "manager" else team_gaps.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    # once, so a real wait still stops; never while a subagent or a background command it waits on still runs
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active") and not background_work.running_work(event.get("transcript_path") or ""):
        goal = [g for g in team_gaps.worker_goal(me) if g.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    size = call and call["title"]
    reason = (f"An issue body changes only by {EDIT_BODY} <issue> <diff-file> \"DECIDED: <why>\", which posts the diff as a comment first, as {GRAMMAR} says." if call and call["body edit"]
              else "Write the text to a scratch file first, then pass it with --body-file." if call and call["inline body"]
              else f"Title is {size} characters; shorten it to 40, verb first. Nothing in this command ran, so write any body file again." if size and size > 40 else None)
    if not reason:  # remind, never block: the command still runs
        text = call and reminder(call, role, event.get("cwd"))
        return text and {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason": reason}}


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
if kind not in ("PreToolUse", "PostToolUse") or board.command((event.get("tool_input") or {}).get("command", "")):  # skip other Bash fast
    listed, me = session.sessions(event.get("session_id"))
    role = team_names.role(me.get("name"))
    if out := role and route(kind, event, role, me, listed):
        print(json.dumps(out))
