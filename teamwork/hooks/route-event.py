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
from json_command import run  # noqa: E402

PLAYBOOKS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
EDIT_BODY = PLAYBOOKS.parent / "scripts" / "edit-issue-body.py"
# only where a command segment starts, so gh text quoted inside another command's argument is not read as a call
GH_TEXT = re.compile(r"(?:^|&&|\|\||[;|(`\n]|\b(?:then|do|else)\s)\s*(?:\w+=\S*\s+)*(gh (?:(?:issue|pr) (?:create|comment|edit|close)|api)\b)")
SEGMENT_END = re.compile(r"&&|\|\||[;|)`]|(?<!\\)\n")  # a backslash-newline continues the command
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
REMINDED = {"gh issue create": ("`file`", "40 characters"), "gh pr create": ("40 characters",), "gh issue comment": ("**Comment**", "`comment`"), "gh pr comment": ("**Comment**",),
            "gh issue close": ("`resolve`",), "gh issue edit": ("edit-issue-body", "40 characters"), "gh pr edit": ("40 characters",)}
REST_WRITE = re.compile(r'issues(?:/(\d+)(/comments)?)?(?=[\s"\'?]|$)')
FENCE = re.compile(r"^```teamwork\n.*?^```", re.S | re.M)
STATE_LINE = re.compile(r"^\s*(holders|deferred):", re.M)
# what gh printed for a posted comment or a filed issue; read back after the command, since a body file is often written by the same command
POSTED = re.compile(r"https://github\.com/([^/\s\"]+/[^/\s\"]+)/issues/(\d+)(?:#issuecomment-(\d+))?")


def rest_call(command):
    """The gh issue command a REST write stands for, so one rule list covers both ways of writing."""
    if not command.startswith("gh api"):
        return command
    method = re.search(r"(?:-X|--method[= ])\s*(\w+)", command)
    method = method.group(1).upper() if method else "POST" if re.search(r"(?<!\S)(-f|-F|--field|--raw-field|--input)\b", command) else "GET"
    path = REST_WRITE.search(command)
    if not path or method not in ("POST", "PATCH"):
        return ""
    if path.group(2):
        return "gh issue comment" if method == "POST" else ""
    if path.group(1):
        return ("gh issue close" if "state=closed" in command else "gh issue edit") if method == "PATCH" else ""
    return "gh issue create" if method == "POST" else ""


def gh_call(command):
    """The first gh issue or pr write the command makes, up to its segment's end; empty when it makes none."""
    found = GH_TEXT.search(command)
    return SEGMENT_END.split(command[found.start(1):])[0] if found else ""


def stray_state(output):
    """The urls of what the command posted with a holders or deferred line outside a teamwork fence, which code never reads."""
    stray = []
    for repo, number, comment in sorted(set(POSTED.findall(output))):
        path = f"repos/{repo}/issues/comments/{comment}" if comment else f"repos/{repo}/issues/{number}"
        body = (run("gh", "api", path) or {}).get("body") or ""
        if STATE_LINE.search(FENCE.sub("", body)):
            stray.append(f"https://github.com/{repo}/issues/{number}" + (f"#issuecomment-{comment}" if comment else ""))
    return stray


def reminder(command, role):
    call = rest_call(command)
    called, needles = next(((c, n) for c, n in REMINDED.items() if call.startswith(c)), (None, ()))
    found = [f"- {path.relative_to(PLAYBOOKS.parents[1])}:{number}: {line.strip()}"
             for path in (PLAYBOOKS.parent / "SKILL.md", PLAYBOOKS / f"{role}.md", GRAMMAR)
             for number, line in enumerate(path.read_text().splitlines(), 1) if any(n in line for n in needles)]
    return found and "\n".join([f"Reminder: the playbook rules this `{called}` must keep:", *found])


def route(kind, event, role, me, listed):
    command = (event.get("tool_input") or {}).get("command", "")
    if kind == "PostToolUse":
        stray = re.match(r"gh (issue|pr) (create|comment|edit)", rest_call(gh_call(command))) and stray_state(json.dumps(event.get("tool_response")))
        return stray and {"decision": "block", "reason": f"A `holders:` or `deferred:` line sits outside a ```teamwork fence in {' '.join(stray)}, so code reads no holder; "
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
    command = gh_call(command)
    title = re.search(r"(?<!\S)(--title|-t)[= ](\"[^\"]*\"|'[^']*'|[^\s\"']\S*)", command)
    size = title and len(title.group(2)) - (2 if title.group(2)[0] in "\"'" else 0)
    reason = (f"An issue body changes only by {EDIT_BODY} <issue> <diff-file> \"DECIDED: <why>\", which posts the diff as a comment first, as {GRAMMAR} says." if re.match(r"gh issue edit\b", command)
              and re.search(r"(?<!\S)(--body-file|-F|--body|-b)[= ]", command)
              else "Write the text to a scratch file first, then pass it with --body-file." if re.search(r"(?<!\S)(--body|-b)[= ]", command)
              else f"Title is {size} characters; shorten it to 40, verb first. Nothing in this command ran, so write any body file again." if size and size > 40 else None)
    if not reason:  # remind, never block: the command still runs
        text = command and reminder(command, role)
        return text and {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason": reason}}


event = json.load(sys.stdin)
kind = event.get("hook_event_name")
if kind not in ("PreToolUse", "PostToolUse") or GH_TEXT.search((event.get("tool_input") or {}).get("command", "")):  # skip other Bash fast
    listed, me = herdr_agents.sessions(event.get("session_id"))
    role = herdr_agents.role(me.get("name"))
    if out := role and route(kind, event, role, me, listed):
        print(json.dumps(out))
