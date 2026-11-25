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
import agent  # noqa: E402
import background_work  # noqa: E402
import board  # noqa: E402
import install_line  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402

PLAYBOOKS = ROOT / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "task-grammar.md"
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
NO_DATA = "A text never carries data"
REMINDED = {"file": ("`file`", "40 characters", NO_DATA), "change": ("40 characters",), "comment": ("**Comment**", "`comment`", NO_DATA), "change comment": ("**Comment**",),
            "resolve": ("`resolve`", NO_DATA), "edit": ("**Body**", "40 characters"), "change edit": ("40 characters",)}
WORKTREES = "/.claude/worktrees/"
# a word the shell hands to a command that only names files or text, so the words after it run nothing
NEVER_RUNS = frozenset("in echo printf grep egrep fgrep rg git cat tee ls head tail wc man which type test tr cut sort uniq jq nl diff less".split())
MENTIONS = NEVER_RUNS | {"mv", "cp"}
SHELLS = re.compile(r"(?:r?ba|da|z|k|mk|pdk|tc|c|y|o|a)?sh(?:-?[\d.]+)?|fish|nu|rc|pwsh")
ISSUE_VERBS = ("create", "new", "comment", "edit", "close", "reopen", "delete", "transfer", "pin", "unpin", "lock", "unlock", "develop")
API_VALUED = ("--method", "--field", "--raw-field", "--input", "--jq", "--header")
SUBSTITUTION = re.compile(r"(?<!\\)\$\(((?:[^()]|\([^()]*\))*)\)|(?<!\\)`((?:\\.|[^`\\])*)`")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)\\?(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
COMMENT = re.compile(r"(?:^|(?<=[ \t;&|(]))#[^\n]*", re.M)
CHANGE_DIRECTORY = re.compile(r"(?:^|[;&|({]|\bthen|\bdo)[ \t]*(?:(?:builtin|command)[ \t]+(?:(?:-p+|--)[ \t]+)*)*(?:cd|pushd)[ \t]+(?:-[A-Za-z@]+[ \t]+)*(?:--[ \t]+)?((?:\"[^\"]*\"|'[^']*'|\$\{[^}\s]*\}|\$\([^)]*\)|`[^`]*`|[^\s;&|)}\"'])+)", re.M)
# what the shell reads as one word or as nothing, in the order it meets it: an escaped character, a single-quoted string, a double-quoted string and the substitutions in it, a bare substitution, a comment
SUBSTITUTED = r"(?:\$\((?:[^()]|\([^()]*\))*\)|`(?:\\.|[^`\\])*`)"
SPANS = re.compile(rf"\\.|'[^']*'|\"(?:\\.|{SUBSTITUTED}|\$(?!\()|[^\"\\$`])*\"|{SUBSTITUTED}|(?<![^\s;&|(])#[^\n]*")
PUNCTUATION = set(";&|()<>\n")


def blanked_bodies(command):
    """COMMAND of the same length with each heredoc body turned into `_`."""
    return HEREDOC.sub(lambda found: found.group(0).partition("\n")[0] + "\n" + "_" * (len(found.group(0)) - len(found.group(0).partition("\n")[0]) - 1), command)


def inert_text(command):
    """COMMAND of the same length with each heredoc body, comment and quoted string turned into `_`, except a `$(...)` the shell runs, even inside double quotes,
    so a cd in it is read as a command and a cd in plain text is not."""
    def blank_quoted(found):
        text, kept = found.group(0), set()
        for substitution in SUBSTITUTION.finditer(text) if text[0] == '"' else ():
            if text[substitution.start()] == "$":
                kept.update(range(*substitution.span()))
        return "".join(char if at in kept or at in (0, len(text) - 1) else "_" for at, char in enumerate(text))
    return COMMENT.sub(lambda found: "_" * len(found.group(0)), QUOTED.sub(blank_quoted, blanked_bodies(command)))


def unquoted(word):
    """WORD as the shell hands it on, its quotes removed, or as written when they never close."""
    try:
        return " ".join(shlex.split(word))
    except ValueError:
        return word


def commands(text, depth=0):
    """The simple commands of TEXT as lists of words, read as the shell reads them: quotes and backslashes removed, a comment dropped, `;`, `&&`, `||`, `|`, `&`, a
    parenthesis and a newline ending a command, a redirect's target left out, and the commands a command runs by other means added, each read the same way: a command
    substitution (also inside double quotes), the code a shell is given by `-c`, `eval`'s words, the heredoc or here-string a shell reads and the words a pipe feeds it;
    nothing for a text that does not parse, since a hook never raises."""
    if depth > 5:
        return []
    inner, bodies = [], []
    text = HEREDOC.sub(lambda found: bodies.append(found[3]) or found[0].partition("\n")[0], text.replace("\\\n", " "))

    def span(found):
        if found[0][0] in "\\'":
            return found[0]
        if found[0][0] == "#":
            return ""
        return SUBSTITUTION.sub(lambda part: inner.append(part[1] if part[1] is not None else part[2]) or "$S", found[0])
    lexer = shlex.shlex(SPANS.sub(span, text), posix=True, punctuation_chars="".join(PUNCTUATION))
    lexer.whitespace_split, lexer.whitespace, lexer.commenters = True, " \t\r", ""
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    rows, row, fed, hold, piped = [], [], [], "", False
    for token in [*tokens, "\n"]:
        if not token or not set(token) <= PUNCTUATION:
            if hold == "<<<":
                fed.append(token)
            elif hold and hold.startswith("<<") and bodies:
                fed.append(bodies.pop(0))
            elif not hold:
                row.append(token)
            hold = ""
        elif "<" in token or ">" in token:
            hold = token
        else:
            rows.append((row, fed, piped))
            row, fed, hold, piped = [], [], "", token == "|"
    found = [words for words, _, _ in rows if words]
    for at, (words, fed, piped) in enumerate(rows):
        for place, word in enumerate(words):
            name = os.path.basename(word)
            if name in NEVER_RUNS:
                break
            if name != "eval" and not SHELLS.fullmatch(name):
                continue
            code = shell_code(name, words[place + 1:])
            before, earlier = rows[at - 1][:2] if piped and at else ([], [])
            fed += [" ".join(next((before[k + 1:] for k, word in enumerate(before) if os.path.basename(word) in NEVER_RUNS), before))] * bool(before) + earlier
            inner += fed if code is None else code
            break
    for text in inner:
        found += commands(text, depth + 1)
    return found


def shell_code(name, args):
    """The text a shell or `eval` called NAME runs from its ARGS: its `-c` code or, for `eval`, its words; None when it reads a script file's or its input's commands, and
    the empty list when it reads a script file."""
    if name == "eval":
        return [" ".join(args)]
    for at, option in enumerate(args):
        if option.startswith("--command="):
            return [option.partition("=")[2]]
        if option in ("--command", "-Command") or re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", option):
            return [next((word for word in args[at + 1:] if not word.startswith("-")), "")]
    return None if all(word.startswith("-") or word in ("/dev/stdin", "/dev/fd/0") for word in args) else []


def after_options(args, names):
    """The place of the first of NAMES in ARGS that only options and their values come before, else None."""
    return next((at for at, word in enumerate(args) if word in names and all(earlier[:1] == "-" or index and args[index - 1][:1] == "-" for index, earlier in enumerate(args[:at]))), None)


def api_writes(args):
    """Whether the words ARGS after `gh api` write to a GitHub issue or its comment: a field, an input file or a method that writes, with no `GET`, on an endpoint of
    issues, or a GraphQL mutation of an issue or comment."""
    method, fields, endpoints, at = "", [], [], 0
    while at < len(args):
        word, at = args[at], at + 1
        if word.startswith("--"):
            name, equals, value = word.partition("=")
            if name in API_VALUED and not equals:
                value, at = args[at] if at < len(args) else "", at + 1
            method = value.upper() if name == "--method" else method
            fields += [value] * (name in ("--field", "--raw-field", "--input"))
        elif word.startswith("-") and len(word) > 1:  # a short flag may sit in a bundle (`-fbody=x`, `-iXPOST`), the first one that takes a value ending it
            place = next((place for place, letter in enumerate(word) if letter in "XfFHqt"), None)
            if place:
                value, at = (word[place + 1:], at) if word[place + 1:] else (args[at] if at < len(args) else "", at + 1)
                method = value.upper() if word[place] == "X" else method
                fields += [value] * (word[place] in "fF")
        else:
            endpoints.append(word)
    if "graphql" in endpoints:
        return any(re.search(r"\bmutation\b.*(?:[Ii]ssue|[Cc]omment)", field, re.S) for field in fields)
    return bool(fields or method in ("POST", "PATCH", "PUT", "DELETE")) and method != "GET" and any(re.search(r"\b(?:issues|sub_issues|dependencies)\b", word) for word in endpoints)


def writes_github_issue(command):
    """True when a command in COMMAND, one it runs by `-c`, `eval`, a substitution or a pipe into a shell included, is `gh issue` with a verb that writes, or `gh api` that
    writes to an issue; `gh` is read as the shell reads it, so `"gh" "issue" "create"` is the same."""
    for words in commands(command):
        for place, word in enumerate(words):
            if os.path.basename(word) in NEVER_RUNS:
                break
            args = words[place + 1:]
            at = after_options(args, ("issue", "api")) if os.path.basename(word) == "gh" else None
            if at is not None and (api_writes(args[at + 1:]) if args[at] == "api" else after_options(args[at + 1:], ISSUE_VERBS) is not None):
                return True
    return False


def directory_before(prefix, cwd):
    """The folder a command written after PREFIX starts in: CWD moved by each `cd` of PREFIX that a `&&`, `;` or `(` carries on to it, and CWD again after any
    other joint, since a pipe, `||`, `&` or a closed subshell leaves the folder as it was."""
    lexer = shlex.shlex(prefix.replace("\n", ";"), posix=True, punctuation_chars=True)
    lexer.wordchars += "$%{}:+@,^!"  # so a variable in a target is one word, not cut at its `$` and braces
    try:
        tokens = list(lexer)
    except ValueError:
        return cwd  # an opened quote hides what it holds, so the cd stays read from CWD
    here, words = cwd, []
    for token in tokens:
        if not set(token) <= set("&|;()"):  # a word, or a redirect such as `2>&1`, which holds `>`
            words.append(token)
            continue
        spelled = words
        while spelled[:1] in (["builtin"], ["command"]):
            spelled = spelled[1:]
            while re.fullmatch(r"-p+|--", (spelled[:1] or [""])[0]):
                spelled = spelled[1:]
        target = next((word for word in spelled[1:] if not word.startswith("-")), None)
        if token not in ("&&", ";", "("):
            here = cwd
        elif spelled[:1] in (["cd"], ["pushd"]) and target:
            here = os.path.normpath(os.path.join(here, os.path.expanduser(target)))
        words = []
    return here


def inside(path, folder):
    """Whether PATH is FOLDER or lies under it, by the file each names, so a symlink or another letter case of FOLDER is it too; a PATH that does not exist yet is
    taken by its nearest folder that does."""
    try:
        want = os.stat(folder)
    except OSError:
        return (path + "/").startswith(folder + "/")
    while True:
        try:
            if os.path.samestat(os.stat(path), want):
                return True
        except OSError:
            pass
        if os.path.dirname(path) == path:
            return False
        path = os.path.dirname(path)


def in_live_checkout(path, root):
    """The folder PATH names, with its `..` read as written or after each symlink before it is resolved (a `cd` and a `cd -P` differ there), where it is in the live checkout ROOT outside its worktrees; else None."""
    return next((found for found in (os.path.normpath(path), os.path.realpath(path)) if inside(found, root) and not inside(found, root + WORKTREES)), None)


def live_change_directory(command, cwd):
    """(folder, worktree): the folder of the live checkout a `cd` in COMMAND enters from the worktree CWD, and the worktree; None for any other cd; a cd,
    never a write, is matched, since a script run after it may write anywhere."""
    root, inside, rest = (cwd or "").partition(WORKTREES)
    worktree = root + WORKTREES + rest.split("/")[0]
    for found in CHANGE_DIRECTORY.finditer(inert_text(command)) if inside else ():  # a cd inside a quote, heredoc or comment runs nothing
        before = blanked_bodies(command[:found.start(1)])
        here = directory_before(before, cwd)
        target = command[found.start(1):found.end(1)]
        if re.search(r"\$|`", target):  # a folder the hook cannot read may be the live checkout
            return target, worktree
        if entered := in_live_checkout(os.path.join(here, os.path.expanduser(unquoted(target))), root):
            return entered, worktree
    return None


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


def reminder(call, role, session_id=None):
    needles = REMINDED.get(call["write"], ())
    found = [f"- {path.relative_to(PLAYBOOKS.parents[1])}:{number}: {line.strip()}"
             for path in (PLAYBOOKS / "protocol.md", PLAYBOOKS / f"{role}.md", GRAMMAR)
             for number, line in enumerate(path.read_text().splitlines(), 1) if any(needle in line for needle in needles)]
    found = unseen(found, session_id)
    return found and "\n".join([f"Reminder: the playbook rules this `{call['called']}` must keep:", *found])


def expanded_path(word):
    """WORD with `${CLAUDE_PLUGIN_ROOT}`, `$CLAUDE_PLUGIN_ROOT`, `$HOME` and a leading tilde written as the folders they name; None when another variable or a substitution is left in it."""
    folders = {"CLAUDE_PLUGIN_ROOT": str(ROOT), "HOME": os.path.expanduser("~")}
    word = os.path.expanduser(re.sub(r"\$\{(CLAUDE_PLUGIN_ROOT|HOME)\}|\$(CLAUDE_PLUGIN_ROOT|HOME)\b", lambda found: folders[found[1] or found[2]], word))
    return None if "$" in word or "`" in word else word


def missing_script(command, cwd):
    """The first script of this plugin the command names by a path that does not exist, with the plugin's files of that name, since a remembered path goes stale; a word of a
    command passes when the command is `mv`, `cp`, `git`, `ls` or another that only names files, when the word follows `-c` or `-m` or another script, and a redirect's target,
    a quoted message, a heredoc body and a comment are no word of a command."""
    for words in commands(command):
        for at, word in enumerate(words):
            path = expanded_path(word)
            if path and path.endswith(".py") and f"/{ROOT.name}/" in path and not re.search(r"\s", path) and not pathlib.Path(cwd or ".", path).exists() \
                    and not (set(map(os.path.basename, words[:at])) & MENTIONS or words[at - 1:at] in (["-c"], ["-m"]) or at and words[at - 1].endswith(".py")):
                return path, sorted(str(file) for file in ROOT.rglob(pathlib.Path(path).name))
    return None


def command_of(event):
    return (event.get("tool_input") or {}).get("command") or ""


def route(kind, event, role, me, listed):
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
    if entered:  # guards the checkout every session loads; it only denies, so every call keeps the person's prompt and the classifier
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"This cd enters {entered[0]}, which is or may be in the live checkout every session loads, so an edit there lands outside your worktree; "
                f"nothing in this command ran; run it again without that cd: a plugin script takes `--repository <folder>` to act on another checkout, git takes `git -C <folder>`, and a file is read by its path, "
                f"since your shell already stands in {entered[1]}."}}
    if kind == "PreToolUse" and writes_github_issue(command_of(event)):
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"Team work (a task, finding, hand-over, question or answer) lives on the git-refs board, never in a GitHub issue; nothing in this command ran. Write it with "
                f"`{PLAYBOOKS.parent / 'scripts' / 'use-board.py'}` with `file`, `comment`, `decide`, `edit` or `resolve`, as {PLAYBOOKS / 'adapters' / 'board.md'} says. When the owner asked for a GitHub issue, "
                "ask them to run the command themselves by typing `! <command>`."}}
    call = board.command(command_of(event))
    text = call and reminder(call, role, event.get("session_id"))
    return text and {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}


def main(args):
    event = json.load(sys.stdin)
    kind = event.get("hook_event_name")
    command = command_of(event)
    if kind == "PreToolUse" and (missing := missing_script(command, event.get("cwd"))):  # any session, since the stale path is the caller's, not its role's
        found = " or ".join(f"`{path}`" for path in missing[1]) or "nothing; find it in the playbook that names it"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                          f"{missing[0]} does not exist, so nothing in this command ran; this plugin has that script at {found}."}}))
        return 0
    # without its host's command no session has a name, so no role matches and the role's SessionStart text never comes to say why
    if kind == "SessionStart" and (missing := next(filter(None, map(install_line.missing, session.NEEDS)), None)):
        print(json.dumps({"systemMessage": missing}))
    elif kind in ("SessionStart", "Stop") \
            or kind == "PreToolUse" and (board.command(command) or writes_github_issue(command) or live_change_directory(command, event.get("cwd"))):  # skip other Bash fast
        listed, me = session.sessions(event.get("session_id"))
        role = team_names.role(me.get("name"))  # first, since a name with no role ends the lookup and `agent.named` walks `ps` and transcripts
        if role and agent.named(me.get("name"), event.get("transcript_path")) and (out := route(kind, event, role, me, listed)):
            print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
