#!/usr/bin/env python3
"""Route each hook event to its role's timing-bound steps, kept in this hook instead of in the playbooks.

usage: route-event.py
It reads one hook event as JSON on stdin and prints the hook's answer, if any, as JSON on stdout."""
import json
import os
import pathlib
import re
import shlex
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import background_work  # noqa: E402
import board  # noqa: E402
import install_line  # noqa: E402
import issue_state  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402

PLAYBOOKS = ROOT / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
REMINDED = {"file": ("`file`", "40 characters"), "change": ("40 characters",), "comment": ("**Comment**", "`comment`"), "change comment": ("**Comment**",),
            "resolve": ("`resolve`",), "edit": ("edit-issue-body", "40 characters"), "change edit": ("40 characters",)}
WORKTREES = "/.claude/worktrees/"
# the only commands whose rewrite is offered: reads, so the live checkout is never written by a command the hook suggests
READ_GIT = {"status", "log", "diff", "show", "grep", "ls-files", "rev-parse", "blame", "describe", "shortlog", "cat-file", "ls-tree"}
READ_ONLY = {"cat", "head", "tail", "wc", "ls", "grep", "rg", "stat", "file", "du", "cut", "tr", "diff", "nl", "tree"}
PATTERN_FIRST = {"grep", "rg"}
# a write to a GitHub issue, by `gh issue` or by `gh api` with a body, a method that writes or a GraphQL issue or comment mutation; `gh` is matched only where
# a command starts, in a text with its quoted strings and heredocs blanked, since a commit message or a grep pattern may name it; what `gh api` is given is read
# unblanked. A reminder against a habit, not a wall: a command built by `eval`-like indirection is not followed.
ASSIGNMENT = r"\w+=(?:\$\([^)]*\)|\S*)"
WRAPPER = rf"(?:command|time|sudo|exec|nohup|timeout(?:[ \t]+-\S+)*[ \t]+\d\S*|watch(?:[ \t]+-\S+(?:[ \t]+\d\S*)?)*|xargs(?:[ \t]+-\S+(?:[ \t]+[^\s-]\S*)?)*|env(?:[ \t]+(?:-\S+|{ASSIGNMENT}))*)"
COMMAND_START = (rf"(?:^|[;&|({{`!\n])[ \t]*(?:(?:then|do)\b[ \t]*)?(?:{ASSIGNMENT}[ \t]+)*(?:{WRAPPER}[ \t]+)*(?:\S*/)?gh\s+"
                 r"(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*")
GITHUB_ISSUE_WRITE = re.compile(COMMAND_START + r"issue\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*"
                                r"(?:create|new|comment|edit|close|reopen|delete|transfer|pin|unpin|lock|unlock|develop)\b", re.M)
GITHUB_API = re.compile(COMMAND_START + r"api\s+(?!graphql)", re.M)
GITHUB_GRAPHQL = re.compile(COMMAND_START + r"api\s+graphql\b", re.M)
API_WRITES = re.compile(r"(?:^|(?<=\s))(?:(?:-X|--method)[\s=]*(?:POST|PATCH|PUT|DELETE)\b|-[fF]\b|--(?:raw-)?field\b|--input\b)")
API_READS = re.compile(r"(?:^|(?<=\s))(?:-X|--method)[\s=]*GET\b")
API_ISSUES = re.compile(r"\b(?:issues|sub_issues|dependencies)\b")
API_FIELD_VALUE = re.compile(r"(?:^|(?<=\s))(?:-[fF]|--(?:raw-)?field)[\s=]*(?:(?:[^\s\"']*(?:\"(?:\\.|[^\"\\])*\"|'[^']*'))+[^\s\"']*|\S+)")
SHELL_STRING = re.compile(r"\b(?:(?:ba|z)?sh[ \t]+-\w*c|eval)[ \t]+(\"(?:\\.|[^\"\\])*\"|'[^']*')")
SUBSTITUTION = re.compile(r"(?<!\\)\$\(((?:[^()]|\([^()]*\))*)\)|(?<!\\)`((?:\\.|[^`\\])*)`")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
CHANGE_DIRECTORY = re.compile(r"(?:^|[;&|({]|\bthen|\bdo)[ \t]*(?:cd|pushd)[ \t]+(?:--[ \t]+)?(\"[^\"]*\"|'[^']*'|[^\s;&|)}]+)", re.M)


def blank_text(command):
    """COMMAND of the same length with each heredoc body and quoted string's inside turned into `_`, so a word inside them is no command."""
    command = HEREDOC.sub(lambda found: found.group(0).partition("\n")[0] + "\n" + "_" * (len(found.group(0)) - len(found.group(0).partition("\n")[0]) - 1), command)
    return QUOTED.sub(lambda found: found.group(0)[0] + "_" * (len(found.group(0)) - 2) + found.group(0)[-1], command)


def unrun_blanked(command):
    """COMMAND of the same length with each single-quoted string and each heredoc body turned into `_`, since a shell runs no substitution inside them."""
    command = HEREDOC.sub(lambda found: found.group(0).partition("\n")[0] + "\n" + "_" * (len(found.group(0)) - len(found.group(0).partition("\n")[0]) - 1), command)
    return re.sub(r"'[^']*'", lambda found: "'" + "_" * (len(found.group(0)) - 2) + "'", command)


def rest_of_command(command, blanked, start):
    """The text of COMMAND from START to the end of its simple command, found in the blanked text, so a `;` inside a quoted body ends nothing."""
    end = re.search(r"[;&|\n]", blanked[start:])
    return command[start:start + end.start()] if end else command[start:]


def writes_github_issue(command):
    """True when COMMAND, or a string it runs by `bash -c`, `eval` or a command substitution, writes to a GitHub issue."""
    command = command.replace("\\\n", " ")
    blanked = blank_text(command)
    if GITHUB_ISSUE_WRITE.search(blanked):
        return True
    for found in GITHUB_API.finditer(blanked):
        rest = rest_of_command(command, blanked, found.end())
        if API_WRITES.search(rest) and not API_READS.search(rest) and API_ISSUES.search(API_FIELD_VALUE.sub(" ", rest)):
            return True
    for found in GITHUB_GRAPHQL.finditer(blanked):
        if re.search(r"\bmutation\b.*(?:[Ii]ssue|[Cc]omment)", rest_of_command(command, blanked, found.end()), re.S):
            return True
    inner = [match.group(1) for match in SHELL_STRING.finditer(command)]
    inner = [text[1:-1] for text in inner] + [command[match.start(1):match.end(1)] if match.group(1) is not None else command[match.start(2):match.end(2)] for match in SUBSTITUTION.finditer(unrun_blanked(command))]
    return any(writes_github_issue(text) for text in inner)


def live_change_directory(command, cwd):
    """(folder, worktree, command): the folder of the live checkout a `cd` in COMMAND enters from the worktree CWD, the worktree, and COMMAND written
    without that cd, None when it cannot be; None for any other cd; a cd, never a write, is matched, since a script run after it may write anywhere."""
    root, inside, rest = (cwd or "").partition(WORKTREES)
    worktree = root + WORKTREES + rest.split("/")[0]
    for found in CHANGE_DIRECTORY.finditer(command) if inside else ():
        path = os.path.normpath(os.path.join(cwd, os.path.expanduser(found[1].strip("\"'"))))
        if (path + "/").startswith(root + "/") and WORKTREES not in path + "/":
            return path, worktree, without_change_directory(command, found, path, worktree)
    return None


def without_change_directory(command, found, folder, worktree):
    """COMMAND with the cd FOUND into FOLDER dropped and each later command written for the shell's own folder, `git -C FOLDER` for git and the absolute
    path for each argument naming something in FOLDER; None unless every command is a read of FOLDER whose rewrite is certain to read the same thing: a write, a
    second cd, an option that may take or write a file, a redirect, expansion, glob, comment, empty or numeric word, or a name that also exists in WORKTREE keeps the refusal's plain message."""
    rest = command[found.end():]
    if re.search(r"[<>$`*?\\\n\[{#~]|\b(?:cd|pushd|popd)\b", rest):
        return None
    lexer = shlex.shlex(rest, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    tail = " )" if tokens[-1:] == [")"] else ""
    tokens = tokens[:-1] if tail else tokens
    if tokens[:1] in (["&&"], [";"]):
        tokens = tokens[1:]
    commands, joint, fresh = [], "", True
    for token in tokens:
        if re.fullmatch(r"&&|\|\||;|\|", token):
            joint, fresh = token, True
        elif re.fullmatch(r"[();|&<>]+", token) or not token:
            return None
        elif fresh:
            commands.append((joint, [token]))
            fresh = False
        else:
            commands[-1][1].append(token)
    if fresh:
        return None
    rewritten = []
    for joint, words in commands:
        if words[0] == "git":
            if words[1:2] and words[1] not in READ_GIT:
                return None
            if any(word.startswith("--output") for word in words):
                return None
            words[1:1] = ["-C", folder]
        elif words[0] in READ_ONLY:
            if any(word.startswith("-") and not re.fullmatch(r"-[A-Za-z0-9]*", word) or re.fullmatch(r"-[A-Za-z]*[foe][A-Za-z]*", word) for word in words[1:]):
                return None  # a long option or one that may take a file or write one leaves a path the rewrite cannot place
            positional = [at for at, word in enumerate(words) if at and not word.startswith("-")]
            changed = False
            for at in positional[1 if words[0] in PATTERN_FIRST else 0:]:
                if words[at].isdigit() or os.path.exists(os.path.join(worktree, words[at])) and not os.path.exists(os.path.join(folder, words[at])):
                    return None
                if os.path.exists(os.path.join(folder, words[at])):
                    words[at], changed = os.path.normpath(os.path.join(folder, words[at])), True
            if not changed and joint != "|":
                return None
        else:
            return None
        rewritten.append((f" {joint} " if joint else "") + " ".join(map(shlex.quote, words)))
    delimiter = re.match(r"[;&|({]|then|do", found[0])
    return command[:found.start()] + (delimiter[0] + " " if delimiter else "") + "".join(rewritten) + tail


def stray_state(call, cwd):
    """A holders line in the posted file that no teamwork fence holds, which code never reads."""
    path = call["body file"] and pathlib.Path(cwd or ".") / call["body file"]
    try:
        return bool(path and issue_state.stray_state(path.read_text()))
    except OSError:
        return False


def stray_posted(output):
    """The url the write printed when a holders line in what it posted sits outside a teamwork fence, read back from the board."""
    url, body = board.posted(output) or (None, "")
    return issue_state.stray_state(body) and url


def unseen(lines, session_id):
    """LINES not yet reminded in this session, recorded so each playbook line is added to the context once; a record that cannot be read or written
    leaves them all unseen, since a reminder must never break the call it decorates."""
    if not session_id:
        return lines
    seen_file = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "teamwork-reminded" / f"{session_id}.txt"
    try:
        seen = set(seen_file.read_text().splitlines()) if seen_file.exists() else set()
        new = [line for line in lines if line not in seen]
        if new:
            seen_file.parent.mkdir(parents=True, exist_ok=True)
            with seen_file.open("a") as fh:
                fh.write("".join(line + "\n" for line in new))
        return new
    except OSError:
        return lines


def reminder(call, role, cwd, session_id=None):
    called, needles = call["called"], REMINDED.get(call["write"], ())
    found = [f"- {path.relative_to(PLAYBOOKS.parents[1])}:{number}: {line.strip()}"
             for path in (PLAYBOOKS / "protocol.md", PLAYBOOKS / f"{role}.md", GRAMMAR)
             for number, line in enumerate(path.read_text().splitlines(), 1) if any(needle in line for needle in needles)]
    found = unseen(found, session_id)
    stray = ["- A `holders:` line sits outside a ```teamwork fence in the posted file, so code reads no holder: put it inside the fence, as "
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


def command_of(event):
    return (event.get("tool_input") or {}).get("command", "")


def route(kind, event, role, me, listed):
    call = board.command(command_of(event))
    if kind == "PostToolUse":
        stray = call and call["write"] in ("file", "comment", "edit") and stray_posted(json.dumps(event.get("tool_response")))
        return stray and verdict(kind, f"A `holders:` line sits outside a ```teamwork fence in {stray}, so code reads no holder; "
                                 f"post the record again with the line inside the fence, as {GRAMMAR} says.", team_settings.load(event.get("cwd") or "."))
    if kind == "SessionStart":
        gaps = (team_gaps.manager_actions(me, listed) if role == "manager" else team_gaps.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    # once, so a real wait still stops; never while a subagent or a background command it waits on still runs
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active") and not background_work.running_work(event.get("transcript_path") or ""):
        goal = [line for line in team_gaps.worker_goal(me) if line.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    entered = role == "worker" and live_change_directory(command_of(event), event.get("cwd"))
    if entered:  # guards the checkout every session loads, no issue rule, so no setting makes it a warning
        again = (f"run this instead: `{entered[2]}`" if entered[2] else "run it again without that cd and read the live checkout by path or git -C")
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"This cd enters {entered[0]} in the live checkout, which every session loads, so an edit there lands outside your worktree; "
                f"nothing in this command ran; {again}, since your shell already stands in {entered[1]}."}}
    if kind == "PreToolUse" and writes_github_issue(command_of(event)):  # no issue rule, so no setting makes it a warning
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"Team work (a task, finding, hand-over, question or answer) lives on the git-refs board, never in a GitHub issue; nothing in this command ran. Write it with "
                f"`{PLAYBOOKS.parent / 'scripts' / 'use-board.py'}` with `file`, `comment`, `decide`, `edit` or `resolve`, as {PLAYBOOKS / 'adapters' / 'board.md'} says. When the owner asked for a GitHub issue, "
                "ask them to run the command themselves by typing `! <command>`."}}
    if not call:
        return None
    settings = team_settings.load(event.get("cwd") or ".")
    size, limit = call["title"], settings["title_max"]
    rule = (f"Title is {size} characters; shorten it to {limit:g}, verb first." + (" Nothing in this command ran, so write any body file again." if settings["refuse"] else "")
            if size and size > limit else None)
    return verdict(kind, rule, settings, None if rule and settings["refuse"] else reminder(call, role, event.get("cwd"), event.get("session_id")))


def main(args):
    event = json.load(sys.stdin)
    kind = event.get("hook_event_name")
    command = command_of(event)
    # without its host's command no session has a name, so no role matches and the role's SessionStart text never comes to say why
    if kind == "SessionStart" and (missing := next(filter(None, map(install_line.missing, session.NEEDS)), None)):
        print(json.dumps({"systemMessage": missing}))
    elif kind not in ("PreToolUse", "PostToolUse") or board.command(command) \
            or kind == "PreToolUse" and (writes_github_issue(command) or live_change_directory(command, event.get("cwd"))):  # skip other Bash fast
        listed, me = session.sessions(event.get("session_id"))
        role = team_names.role(me.get("name"))
        if out := role and route(kind, event, role, me, listed):
            print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
