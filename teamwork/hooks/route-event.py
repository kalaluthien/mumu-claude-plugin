#!/usr/bin/env python3
"""Route each hook event to its role's timing-bound steps, kept in this hook instead of in the playbooks.

usage: route-event.py
It reads one hook event as JSON on stdin and prints the hook's answer, if any, as JSON on stdout."""
import collections
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
# a write to a GitHub issue, by `gh issue` or by `gh api` with a body, a method that writes or a GraphQL mutation of a GitHub issue or comment. A `gh`, shell or `eval`
# word runs when it opens a simple command or follows only words that are no NEVER_RUNS word, such as a wrapper and its flags, read in a text with its
# quoted strings, substitutions, comments and heredoc bodies blanked, since a commit message, a grep pattern or a note may name it; what it is given is read
# unblanked. A shell or `eval` runs its `-c` code or its words, else the heredoc or here-string it reads and the text a pipe feeds it; a command
# substitution runs its inside. A reminder against a habit, not a wall: a command a variable, a function, a group or a script file names is not followed.
# a word that runs none of the words after it, so a command word behind it is a mention
NEVER_RUNS = r"in|echo|printf|grep|egrep|fgrep|rg|git|cat|tee|ls|head|tail|wc|man|which|type|test|tr|cut|sort|uniq|jq|nl|diff|less"
WORD_START = rf"(?:^|[;&|(){{`!\n])[ \t]*(?:(?!(?:\S*/)?(?:{NEVER_RUNS})[ \t])[^\s;&|()<>]+[ \t]+)*?(?:\S*/)?"
COMMAND_START = WORD_START + r"gh\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*"
GITHUB_ISSUE_WRITE = re.compile(COMMAND_START + r"issue\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*"
                                r"(?:create|new|comment|edit|close|reopen|delete|transfer|pin|unpin|lock|unlock|develop)\b", re.M)
GITHUB_API = re.compile(COMMAND_START + r"api\s+(?!graphql)", re.M)
GITHUB_GRAPHQL = re.compile(COMMAND_START + r"api\s+graphql\b", re.M)
API_WRITES = re.compile(r"(?:^|(?<=\s))(?:(?:-X|--method)[\s=]*(?:POST|PATCH|PUT|DELETE)\b|-[fF]\b|--(?:raw-)?field\b|--input\b)")
API_READS = re.compile(r"(?:^|(?<=\s))(?:-X|--method)[\s=]*GET\b")
API_ISSUES = re.compile(r"\b(?:issues|sub_issues|dependencies)\b")
API_FIELD_VALUE = re.compile(r"(?:^|(?<=\s))(?:-[fF]|--(?:raw-)?field)[\s=]*(?:(?:[^\s\"']*(?:\"(?:\\.|[^\"\\])*\"|'[^']*'))+[^\s\"']*|\S+)")
SHELL_START = re.compile(WORD_START + r"((?:r?ba|da|z|k|mk|pdk|tc|c|y|o|a)?sh(?:-?[\d.]+)?|fish|nu|rc|pwsh|eval)(?![\w.-])", re.M)
PIPELINE_START = re.compile(r";|&&|\|\||(?<![|<>&])&(?![&>])|(?<![|&][ \t])(?<![|&])\n")
LOOSE_WRITE = re.compile(r"(?:\b|(?<=\\[nt]))gh\b[^\n]*?\b(?:issue\b[^\n]*?\b(?:create|new|comment|edit|close|reopen|delete|transfer|pin|unpin|lock|unlock|develop)\b"
                         r"|api\b[^\n]*?(?:(?:-X|--method)[\s=]*(?:POST|PATCH|PUT|DELETE)\b|(?<!\S)-[fF]\b|--(?:raw-)?field\b|--input\b|\bmutation\b))")
SUBSTITUTION = re.compile(r"(?<!\\)\$\(((?:[^()]|\([^()]*\))*)\)|(?<!\\)`((?:\\.|[^`\\])*)`")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)\\?(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
HERE_STRING = re.compile(r"<<<[ \t]*(\"(?:\\.|[^\"\\])*\"|'[^']*'|(?:\\.|[^\s\\])+)")
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
COMMENT = re.compile(r"(?:^|(?<=[ \t;&|(]))#[^\n]*", re.M)
CHANGE_DIRECTORY = re.compile(r"(?:^|[;&|({]|\bthen|\bdo)[ \t]*(?:(?:builtin|command)[ \t]+(?:(?:-p+|--)[ \t]+)*)*(?:cd|pushd)[ \t]+(?:-[A-Za-z@]+[ \t]+)*(?:--[ \t]+)?((?:\"[^\"]*\"|'[^']*'|\$\{[^}\s]*\}|\$\([^)]*\)|`[^`]*`|[^\s;&|)}\"'])+)", re.M)
ASSIGNMENT = r"[ \t]*(?:export[ \t]+)?([A-Za-z_]\w*)=(\"[^\"$`\\]*\"|'[^']*'|[^\s;&|()$`\"'\\]*)[ \t]*(?:&&|;|\n)"  # a value with an expansion is left out, since its result is unknown here
ASSIGNED = re.compile(f"(?:^|(?<=[;&|(\\n])){ASSIGNMENT}")
SHELL_SET = {"OLDPWD", "SHLVL", "_", "PPID", "RANDOM", "LINENO", "SECONDS"}  # names the shell sets for itself, so the hook's copy is no value of the shell's
UNREAD_VARIABLE = re.compile(r"\$[\w{(]|`")
VARIABLE = re.compile(r"\$(\w+)|\$\{(\w+)\}")
ANSI_QUOTED = re.compile(r"\$'((?:\\.|[^'\\])*)'")


def blanked_bodies(command):
    """COMMAND of the same length with each heredoc body turned into `_`."""
    return HEREDOC.sub(lambda found: found.group(0).partition("\n")[0] + "\n" + "_" * (len(found.group(0)) - len(found.group(0).partition("\n")[0]) - 1), command)


def blank_inside(found, opening):
    """The text FOUND matched, kept for its OPENING characters and its last one, and `_` between."""
    return found.group(0)[:opening] + "_" * (len(found.group(0)) - opening - 1) + found.group(0)[-1]


def blank_text(command):
    """COMMAND of the same length with each heredoc body, command substitution's, quoted string's inside and comment turned into `_`, so a word inside
    them is no command and a quote inside a substitution closes none outside it; a substitution is read by itself."""
    command = SUBSTITUTION.sub(lambda found: blank_inside(found, 2 if found.group(0)[0] == "$" else 1), blanked_bodies(command))
    command = QUOTED.sub(lambda found: blank_inside(found, 1), command)
    return COMMENT.sub(lambda found: "_" * len(found.group(0)), command)


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


def rest_of_command(command, blanked, start):
    """The text of COMMAND from START to the end of its simple command, found in the blanked text, so a `;` inside a quoted body ends nothing."""
    end = re.search(r"[;|\n]|(?<![<>])&(?!>)", blanked[start:])
    return command[start:start + end.start()] if end else command[start:]


def unquoted(word):
    """WORD as the shell hands it on, its quotes removed, or as written when they never close."""
    try:
        return " ".join(shlex.split(word))
    except ValueError:
        return word


def shell_writes(command, blanked, found):
    """Whether the shell or `eval` FOUND in BLANKED, the blanked COMMAND, writes to a GitHub issue: by its `-c` code or by the words `eval` runs; else, when
    it reads its input rather than a script file, by the heredoc or here-string it reads, or by a write in the text the stages before it in its pipeline
    print, since that text is what it runs."""
    rest = rest_of_command(command, blanked, found.end())
    lexer = shlex.shlex(rest, posix=True, punctuation_chars="<>&()")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return bool(LOOSE_WRITE.search(rest))
    redirect = [bool(token) and set(token) <= set("<>&") for token in tokens] + [False]
    words = [token for at, token in enumerate(tokens) if not redirect[at] and not (at and redirect[at - 1]) and not (token.isdigit() and redirect[at + 1])
             and token.strip("()")]
    if found.group(1) == "eval":
        return writes_github_issue(" ".join(words[words[:1] == ["--"]:]))
    for at, option in enumerate(words):
        if option.startswith("--command="):
            return writes_github_issue(option.partition("=")[2])
        if option in ("--command", "-Command") or option[:1] == "-" and option[1:2] != "-" and "c" in option[1:]:
            return writes_github_issue(next((word for word in words[at + 1:] if not word.startswith("-")), ""))
    operand = 0
    while operand < len(words) and words[operand][:1] in "-+" and words[operand] not in ("-", "--"):
        operand += 2 if words[operand][1:2] != "-" and words[operand][-1] in "oO" else 1
    if "--version" in words[:operand] or "--help" in words[:operand] or words[operand:] and words[operand] not in ("-", "--", "/dev/stdin", "/dev/fd/0"):
        return False
    end = found.end() + len(rest)
    start = max((match.end() for match in PIPELINE_START.finditer(blanked, 0, found.start() + 1)), default=0)
    fed = [HEREDOC, HERE_STRING]
    own = [match for pattern in fed for match in pattern.finditer(command) if found.end() <= match.start() < end]
    before = [match for pattern in fed for match in pattern.finditer(command) if start <= match.start() < found.start()]
    return any(writes_github_issue(match.group(3) if match.re is HEREDOC else unquoted(match.group(1))) for match in own) or bool(
        LOOSE_WRITE.search("\n".join([command[start:found.start()]] + [match.group(match.lastindex) for match in before])))


def writes_github_issue(command):
    """True when COMMAND, a shell or `eval` it runs, or a command substitution it runs, writes to a GitHub issue."""
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
    if any(shell_writes(command, blanked, found) for found in SHELL_START.finditer(blanked)):
        return True
    unrun = re.sub(r"'[^']*'", lambda found: "'" + "_" * (len(found.group(0)) - 2) + "'", blanked_bodies(command))
    return any(writes_github_issue(command[found.start(1):found.end(1)] if found.group(1) is not None else command[found.start(2):found.end(2)])
               for found in SUBSTITUTION.finditer(unrun))


def ansi_decoded(text):
    """TEXT with each ANSI-C quoted `$'...'` it holds written as the single-quoted string the shell reads, and each `$"..."` as `"..."`; an ANSI-C string whose
    escapes are more than a hex pair or an octal triple of a non-NUL ASCII character is left as written, since the shell may read it otherwise (it cuts a word at a
    NUL, which `\\c@` and `\\400` also make), and the hook cannot read it."""
    def decode(found):
        if not re.fullmatch(r"(?:[^\\]|\\x[0-9a-fA-F]{2}|\\[0-3][0-7]{2})*", found[1]):
            return found[0]
        plain = re.sub(r"\\x([0-9a-fA-F]{2})|\\([0-3][0-7]{2})", lambda escape: chr(int(escape[1] or escape[2], 16 if escape[1] else 8)), found[1])
        return shlex.quote(plain) if plain.isascii() and "\0" not in plain else found[0]
    return ANSI_QUOTED.sub(decode, re.sub(r'\$("(?:\\.|[^"\\])*")', r"\1", text))


def replaced(text, name, value):
    """TEXT with each `$NAME` and `${NAME}` outside single quotes replaced by VALUE."""
    parts = re.split(r"('[^']*')", text)
    return "".join(part if at % 2 else VARIABLE.sub(lambda found: value if (found[1] or found[2]) == name else found[0], part) for at, part in enumerate(parts))


def expanded(word, before, folder):
    """[WORD, ...] with each `$NAME` and `${NAME}` it holds replaced by every value a plain assignment in BEFORE gave it, wherever the shell may skip it, else by the
    hook's environment, which the shell inherits, with `PWD` as FOLDER; a name stays as written when BEFORE assigns it in any form this cannot read, such as two
    to a statement, a value of joined quotes or one that expands, and so does a name with no value. A single-quoted part of WORD stays as it is, since the shell
    expands nothing in it, and assignments are read from the text the shell runs, so one inside a quote or comment counts for none."""
    inert = inert_text(before)
    given = {}
    for found in ASSIGNED.finditer(inert):
        given.setdefault(found[1], []).append(before[found.start(2):found.end(2)].strip("\"'"))
    spelled = collections.Counter(re.findall(r"(?<![\w$])([A-Za-z_]\w*)\+?=", inert))
    values = {name: [value] for name, value in os.environ.items() if name not in SHELL_SET} | {"PWD": [folder]} | given
    values = {name: options for name, options in values.items() if not spelled[name] or spelled[name] == len(given.get(name, ()))}
    texts = [word]
    for name in {found[1] or found[2] for found in VARIABLE.finditer(word)} & values.keys():
        texts = [replaced(text, name, value) for text in texts for value in values[name]]
    return texts


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
            here = os.path.normpath(os.path.join(here, os.path.expanduser(expanded(target, prefix, here)[-1])))
        words = []
    return here


def live_change_directory(command, cwd):
    """(folder, worktree): the folder of the live checkout a `cd` in COMMAND enters from the worktree CWD, and the worktree; None for any other cd; a cd,
    never a write, is matched, since a script run after it may write anywhere."""
    root, inside, rest = (cwd or "").partition(WORKTREES)
    worktree = root + WORKTREES + rest.split("/")[0]
    for found in CHANGE_DIRECTORY.finditer(inert_text(command)) if inside else ():  # a cd inside a quote, heredoc or comment runs nothing
        before = blanked_bodies(command[:found.start(1)])
        here = directory_before(before, cwd)
        targets = expanded(ansi_decoded(command[found.start(1):found.end(1)]), before, here)
        for target in targets:  # a variable the shell may have set either way is read as each value, and none of them is rewritten
            path = os.path.normpath(os.path.join(here, os.path.expanduser(unquoted(target))))
            if (path + "/").startswith(root + "/") and WORKTREES not in path + "/":
                return path, worktree
        unread = next((target for target in targets if UNREAD_VARIABLE.search(outside_single_quotes(target)) or ANSI_QUOTED.search(target)), None)
        if unread:  # a folder the hook cannot read may be the live checkout
            return unread, worktree
    return None


def outside_single_quotes(word):
    """WORD without its single-quoted spans, where an apostrophe inside double quotes quotes nothing."""
    kept, quote, escaped = "", "", False
    for char in word:
        if quote == "'":
            quote = "" if char == "'" else quote
        elif escaped:
            kept, escaped = kept + char, False
        elif char == "\\":
            kept, escaped = kept + char, True
        elif quote == '"':
            kept, quote = kept + char, "" if char == '"' else quote
        elif char in "'\"":
            quote = char
            kept += char if char == '"' else ""
        else:
            kept += char
    return kept


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


def missing_script(command, cwd):
    """The first script of this plugin the command names by a path that does not exist, with the plugin's files of that name, since a remembered path goes stale."""
    for word in re.findall(r"[^\s'\"=]+\.py\b", command):
        path = pathlib.Path(cwd or ".") / word
        if f"/{ROOT.name}/" in word and not path.exists():
            return word, sorted(str(found) for found in ROOT.rglob(path.name) if "fixtures" not in found.parts)
    return None


def command_of(event):
    return (event.get("tool_input") or {}).get("command", "")


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
                f"nothing in this command ran; run it again without that cd and read the live checkout by path or git -C, since your shell already stands in {entered[1]}."}}
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
        role = team_names.role(me.get("name")) if agent.named(me.get("name"), event.get("transcript_path")) else None
        if out := role and route(kind, event, role, me, listed):
            print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
