#!/usr/bin/env python3
"""Timing-bound steps live in this hook, routed per event and role, instead of in the playbooks."""
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import background_work  # noqa: E402
import board  # noqa: E402
import json_command  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
EDIT_BODY = PLAYBOOKS.parent / "scripts" / "edit-issue-body.py"
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
REMINDED = {"file": ("`file`", "40 characters"), "change": ("40 characters",), "comment": ("**Comment**", "`comment`"), "change comment": ("**Comment**",),
            "resolve": ("`resolve`",), "edit": ("edit-issue-body", "40 characters"), "change edit": ("40 characters",)}
FENCE = re.compile(r"^```teamwork\n.*?^```", re.S | re.M)
STATE_LINE = re.compile(r"^\s*(holders|deferred):", re.M)
WORKTREES = "/.claude/worktrees/"
CD = re.compile(r"(?:^|[;&|({]|\bthen|\bdo)[ \t]*(?:cd|pushd)[ \t]+(?:--[ \t]+)?(\"[^\"]*\"|'[^']*'|[^\s;&|)}]+)", re.M)


def live_cd(command, cwd):
    """(folder, worktree): the folder of the live checkout a `cd` in COMMAND enters from the worktree CWD, None for any other;
    a cd, never a write, is matched, since a script run after it may write anywhere."""
    root, inside, rest = (cwd or "").partition(WORKTREES)
    for target in CD.findall(command) if inside else ():
        path = os.path.normpath(os.path.join(cwd, os.path.expanduser(target.strip("\"'"))))
        if (path + "/").startswith(root + "/") and WORKTREES not in path + "/":
            return path, root + WORKTREES + rest.split("/")[0]
    return None


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


def verdict(kind, rule, settings, text=None):
    """The hook's answer to a call that breaks RULE: a refusal when the repository's settings set `refuse`, else a `Warning:` beside TEXT, the reminder."""
    warnings = settings["warnings"]
    if rule and settings["refuse"]:
        reason = "\n".join([rule, *warnings])
        return ({"decision": "block", "reason": reason} if kind == "PostToolUse"
                else {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason": reason}})
    lines = [team_settings.warning(rule)] if rule else []
    context = "\n".join([*lines, *([text] if text else []), *warnings])
    return context and {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": context}}


def route(kind, event, role, me, listed):
    call = board.command((event.get("tool_input") or {}).get("command", ""))
    if kind == "PostToolUse":
        stray = call and call["write"] in ("file", "comment", "edit") and stray_posted(json.dumps(event.get("tool_response")))
        return stray and verdict(kind, f"A `holders:` or `deferred:` line sits outside a ```teamwork fence in {stray}, so code reads no holder; "
                                 f"post the record again with the line inside the fence, as {GRAMMAR} says.", team_settings.load(event.get("cwd") or "."))
    if kind == "SessionStart":
        gaps = (team_gaps.manager_actions(me, listed) if role == "manager" else team_gaps.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    # once, so a real wait still stops; never while a subagent or a background command it waits on still runs
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active") and not background_work.running_work(event.get("transcript_path") or ""):
        goal = [g for g in team_gaps.worker_goal(me) if g.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    entered = role == "worker" and live_cd((event.get("tool_input") or {}).get("command", ""), event.get("cwd"))
    if entered:  # guards the checkout every session loads, no issue rule, so no setting makes it a warning
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"This cd enters {entered[0]} in the live checkout, which every session loads, so an edit there lands outside your worktree; "
                f"start it with cd {entered[1]}, since the shell may start in the live checkout, and read the live checkout by path or git -C."}}
    if not call:
        return None
    settings = team_settings.load(event.get("cwd") or ".")
    size, limit = call["title"], settings["title_max"]
    rule = (f"An issue body changes only by {EDIT_BODY} <issue> <diff-file> \"DECIDED: <why>\", which posts the diff as a comment first, as {GRAMMAR} says." if call["body edit"]
            else "Write the text to a scratch file first, then pass it with --body-file." if call["inline body"]
            else f"Title is {size} characters; shorten it to {limit:g}, verb first." + (" Nothing in this command ran, so write any body file again." if settings["refuse"] else "")
            if size and size > limit else None)
    return verdict(kind, rule, settings, None if rule and settings["refuse"] else reminder(call, role, event.get("cwd")))


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
command = (event.get("tool_input") or {}).get("command", "")
# without herdr no session has a name, so no role matches and the role's SessionStart text never comes to say why
if kind == "SessionStart" and (missing := json_command.missing("herdr")):
    print(json.dumps({"systemMessage": missing}))
elif kind not in ("PreToolUse", "PostToolUse") or board.command(command) or kind == "PreToolUse" and live_cd(command, event.get("cwd")):  # skip other Bash fast
    listed, me = session.sessions(event.get("session_id"))
    role = team_names.role(me.get("name"))
    if out := role and route(kind, event, role, me, listed):
        print(json.dumps(out))
