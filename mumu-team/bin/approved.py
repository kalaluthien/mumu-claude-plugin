#!/usr/bin/env python3
"""Refuse a `gh pr merge` that is not pinned to a sha a reviewer approved, and a git hook bypass.

PreToolUse hook on Bash. A closed heredoc body is dropped only when every
command on its opener's line is a text reader (`cat`, `gh`, `git`, `tee`), no
pipe follows the opener, and the body is quoted or holds no `$(` or backtick;
openers are found outside quotes and comments. The rest is split into commands as
a shell would split it -- at a newline, `;`, `&&`, `|` or `(` -- and in each one every
`pr [-R <repo>]... merge`, counted with quotes, backslashes and redirects
removed, must be the one `gh ... pr merge` that command runs, after an env
prefix or a wrapper such as `rtk`. Every quoted word is counted inside too, but
a text one without `$(` or a backtick: a `grep` or `rg` pattern, or the value of a
message or body flag (`-m`, `--body`, `--comment`, ...) of `gh` or `git`. That merge passes only
when it names one PR by its url, combines no short flags and holds no `{`, `}`,
`*`, `?` or `[` a shell would expand, and only when it carries one
`--match-head-commit <sha>` of 40 hex digits, that sha is the PR's head, and the
PR holds a comment or a review whose first line is `Approved <sha>`. Any other
`pr merge` -- inside `bash -c`, `eval`, `watch`, `$(...)`, a heredoc another
command reads, a here-string, a comment, or a command that cannot be lexed -- is
refused; text only naming it as above passes. A merge built from a variable or an
escape code such as `$'\x6d'` is not seen. A payload or a PR that
cannot be read is refused too (exit 2).

A command that skips a git hook is refused too, in any command and inside a quoted
word: `--no-verify` or an abbreviation of it after `git`, `-n` in a `git commit`
flag cluster (not a value such as `-m -n`), and setting `core.hooksPath` by
`-c`, `--config-env`, `git config <key> <value>` or a `GIT_CONFIG_KEY_*` variable;
text only naming it -- a heredoc body, a message, `echo`, `grep`, a read
`git config <key>` -- passes, even when the command cannot be lexed. A command naming
none of `merge`, `git` or `hookspath` exits 0 unread.
"""
import json
import os
import re
import shlex
import subprocess
import sys

SEPARATORS = set(";&|()\n")
DESCRIPTOR = re.compile(r"(^|[\s;&|()])(?:\d+|\{\w+\})(?=[<>])")
QUOTING = re.compile(r"[\"'\\]")
MENTION = re.compile(r"\bpr\b[\s\S]*?\bmerge\b")
HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][\w.-]*)\2")
RUNS = re.compile(r"\$\(|`")
WORD = re.compile(r"[^\s;&|()<>`'\"]+")
ASSIGNMENT = re.compile(r"\w+=")
BODY_READERS = {"cat", "gh", "git", "tee"}  # each reads a heredoc as text, never as a command
TEXT_COMMANDS = {"grep", "egrep", "fgrep", "rg"}  # each reads its quoted words as text
TEXT_FLAGS = {"-m", "--message", "-b", "--body", "-t", "--title", "--comment", "--subject", "--notes"}  # of gh and git
HOOKS_PATH = re.compile(r"^(['\"]?|--config-env=|GIT_CONFIG_KEY_\d+=['\"]?)core\.hookspath(['\"]?=|['\"]?$)", re.I)  # `-c k=v`, `'k'=v`, `--config-env=k=V`, `KEY_0=k`
HOOKS_PATH_TEXT = re.compile(r"(-c\s*|--config-env=|key_\d+=)core\.hookspath\b|\bconfig\b(?![^;&|\n]*\bget\b)[^;&|\n]*core\.hookspath[ \t]+[^\s;&|]")


def refuse(reason):
    print(f"approved: {reason}", file=sys.stderr)
    sys.exit(2)


def segments(text, join=True):
    """Split text into the word lists of its commands, as a shell would split it."""
    text = DESCRIPTOR.sub(r"\1", text.replace("\\\n", "" if join else " \n"))  # a `\` line joined or not; `2>&1`, `{fd}>x`
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""  # a comment's words are read too, so none hides a merge
    segment = []
    for word in list(lexer) + [";"]:
        if word and set(word) <= SEPARATORS:
            if segment:
                yield segment
            segment = []
        else:
            segment.append(word)


def scan(line, stack):
    """Read one line as a shell would: its heredoc openers, the command words it runs, and whether a pipe follows an opener."""
    openers, heads, piped, start, j = [], [], False, True, 0
    while j < len(line):
        c, context = line[j], stack[-1] if stack else None
        if context == "'":
            stack.pop() if c == "'" else None
        elif c == "\\":
            j += 1
        elif line.startswith("$(", j):
            stack.append("(")
            start, j = True, j + 1
        elif context == '"':
            stack.pop() if c == '"' else stack.append("`") if c == "`" else None
            start = c == "`"
        elif c == "#" and (j == 0 or line[j - 1] in " \t;&|("):  # a comment
            break
        elif c in "'\"(" or c == "`" and context != "`":
            stack.append(c)
            start = c in "(`"
        elif c == ")" and context == "(" or c == "`" and context == "`":
            stack.pop()
        elif c in ";&|":
            piped |= c == "|" and bool(openers)
            start = True
        elif line.startswith("<<", j) and not line.startswith("<<<", j) and HEREDOC.match(line, j):
            openers.append(HEREDOC.match(line, j))
            j = openers[-1].end() - 1
        elif start and WORD.match(line, j):
            word = WORD.match(line, j)[0]
            if not ASSIGNMENT.match(word):
                heads.append(os.path.basename(word))
                start = False
            j += len(word) - 1
        elif not c.isspace():
            start = False
        j += 1
    return openers, heads, piped


def without_heredocs(text):
    """Drop each closed heredoc body that only a text reader reads, quoted or without `$(`; keep every other body as commands."""
    lines, kept, stack, i = text.split("\n"), [], [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        i += 1
        openers, heads, piped = scan(line, stack)
        for opener in openers:
            end = next((j for j in range(i, len(lines))
                        if (lines[j].lstrip("\t") if opener[1] else lines[j]) == opener[3]), None)
            if end is None:  # an unclosed body: read the rest as commands
                break
            body = lines[i:end]
            if piped or not set(heads) <= BODY_READERS or not opener[2] and RUNS.search("\n".join(body)):
                kept += body
            i = end + 1
    return "\n".join(kept)


def text_word(words, i):
    """Whether words[i] is only text: a grep pattern, or a message or body flag's value of gh or git."""
    if RUNS.search(words[i]):
        return False
    head = next((os.path.basename(w) for w in words if not ASSIGNMENT.match(w)), "")
    return head in TEXT_COMMANDS or head in ("gh", "git") and \
        (i > 0 and words[i - 1] in TEXT_FLAGS or words[i].split("=", 1)[0] in TEXT_FLAGS)


def unredirected(words):
    """Drop each redirect: its operator and its target."""
    kept, skip = [], False
    for word in words:
        if word and set(word) <= set("<>&|") and set(word) & set("<>"):
            skip = True
        elif skip:
            skip = False
        else:
            kept.append(word)
    return kept


def mentions(words):
    """Count `pr [-R <repo>]... merge` in the words, and in each word but a text one, which a shell could run."""
    count = 0
    for i, word in enumerate(words):
        if text_word(words, i):
            continue
        word = QUOTING.sub("", word).strip()
        try:
            inner = list(segments(word))
        except ValueError:  # an unclosed quote
            count += len(MENTION.findall(word))
            continue
        if inner != [[word]] and set(word) - set(";&|()<>"):  # a word that splits is text a shell could run
            count += sum(mentions(words) for words in inner)
    words = [QUOTING.sub("", word).strip() for word in unredirected(words)]
    for i, word in enumerate(words):
        if word != "merge":
            continue
        j = i - 1
        while j >= 0 and words[j] != "pr":
            if words[j].startswith("--repo="):
                j -= 1
            elif j >= 1 and words[j - 1] in ("-R", "--repo"):
                j -= 2
            else:
                break
        count += j >= 0 and words[j] == "pr"
    return count


def gh_merge(words):
    for i, word in enumerate(words):
        if os.path.basename(word) != "gh":
            continue
        rest = words[i + 1:]
        for expected in ("pr", "merge"):  # `-R <repo>` may stand before `pr` or before `merge`
            while rest and (rest[0] in ("-R", "--repo") and len(rest) >= 2 or rest[0].startswith("--repo=")):
                rest = rest[1:] if rest[0].startswith("--repo=") else rest[2:]
            if rest[:1] != [expected]:
                break
            rest = rest[1:]
        else:
            yield rest


def target(args):
    """Read the merge's words as gh does: its one PR url and its one head pin."""
    takes_value = {"-R", "--repo", "--match-head-commit", "-b", "--body", "-F", "--body-file",
                   "-t", "--subject", "-A", "--author-email"}
    if any(set(arg) & set("`${}*?[") or arg == "--" for arg in args):  # a shell may expand one word into several
        refuse("write `gh pr merge` without `` ` ``, `$`, `{`, `}`, `*`, `?`, `[` or `--`, so its words are the ones gh gets")
    names, pins, flag = [], [], None
    for arg in args:
        if flag:
            pins += [arg] if flag == "--match-head-commit" else []
            flag = None
        elif re.fullmatch(r"-[A-Za-z]{2,}.*", arg):  # gh reads `-sb 31` as `-s -b 31`
            refuse(f"write `{arg}` as separate flags, so the PR the hook reads is the one gh merges")
        elif arg in takes_value:
            flag = arg
        elif arg.startswith("--match-head-commit="):
            pins.append(arg.split("=", 1)[1])
        elif not arg.startswith("-"):
            names.append(arg)
    if len(pins) != 1 or not re.fullmatch(r"[0-9a-f]{40}", pins[0]):
        refuse("`gh pr merge` must carry one `--match-head-commit <sha>`, the full sha the reviewer approved")
    if len(names) != 1:
        refuse(f"`gh pr merge` must name exactly one PR by number or url, not {names or 'none'}")
    if not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+", names[0]):
        refuse(f"name the PR by its url, not `{names[0]}`: a url fixes the PR whatever `-R`, `GH_REPO` or the directory say")
    return names[0], pins[0]


def bypasses(words):
    """Whether the words skip a git hook: `--no-verify` or its abbreviation, `git commit -n`, or setting `core.hooksPath`."""
    words = unredirected(words)
    for i, word in enumerate(words):
        for join in (True, False):  # `\` then a newline joins lines, unless the `\` is escaped or in a comment
            try:
                inner = list(segments(word, join))
            except ValueError:  # an apostrophe in a message
                inner = [[word]]
            if inner != [[word]] and any(bypasses(w) for w in inner):  # `bash -c '...'`
                return True
        if words[i - 1:i] == ["-c"] and HOOKS_PATH.search(word) or word[:1] in "-G" and HOOKS_PATH.search(word) \
                or word.lower() == "core.hookspath" and config_value(words, i):
            return True
        rest = words[i + 1:] if os.path.basename(word) == "git" else []
        while rest and rest[0].startswith("-"):  # git's own options; these take a value
            rest = rest[2:] if rest[0] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--attr-source") else rest[1:]
        args = iter(rest[1:])
        for arg in args:
            flags = re.match(r"-([^-mFCctSu]*)([mFCct]?)(.*)", arg)  # `-am x`: letters, then one taking a value
            if len(arg) >= 6 and "--no-verify".startswith(arg) or rest[0] == "commit" and flags and "n" in flags[1]:
                return True
            if arg == "--":
                break
            if flags and flags[2] and not flags[3]:  # `-m -n`: `-n` is the message
                next(args, None)
    return False


def config_value(words, i):
    """Whether words[i] is the key `git config [flags] <key> <value>` sets, not the one it reads."""
    before = words[:i]
    if "config" not in before or i + 1 >= len(words):
        return False
    j = before.index("config")
    return any(os.path.basename(w) == "git" for w in before[:j]) and \
        not {"get", "--get", "--get-all", "--get-regexp"} & set(before[j + 1:])


def bypass_text(text):
    """In text that cannot be lexed: `--no-v`, setting `core.hookspath` by `-c`, `--config-env`, `KEY_0=` or `git config <key> <value>`, or a `-...n` flag after `git ... commit`, in linear time."""
    text = QUOTING.sub("", text.replace("\\\n", "")).lower()
    git = re.search(r"\bgit\b", text)
    commit = git and re.compile(r"\bcommit\b").search(text, git.end())
    return "--no-v" in text or bool(HOOKS_PATH_TEXT.search(text)) or bool(commit and re.compile(r"\s-[a-z]*n").search(text, commit.end()))


def check(args, cwd):
    url, sha = target(args)
    view = ["gh", "pr", "view", url, "--json", "headRefOid,comments,reviews"]
    run = subprocess.run(view, capture_output=True, text=True, cwd=cwd)
    try:
        pr = json.loads(run.stdout) if run.returncode == 0 else None
        head = pr["headRefOid"]
    except (ValueError, KeyError, TypeError):
        refuse(f"could not read the PR ({' '.join(view)}): {run.stderr.strip() or run.stdout.strip()}")
    if sha != head:
        refuse(f"--match-head-commit {sha} is not the PR head {head}; the approval, if any, is stale")
    notes = (pr.get("comments") or []) + (pr.get("reviews") or [])
    first_lines = [n["body"].strip().splitlines()[0].strip() for n in notes if n["body"].strip()]
    if f"Approved {head}" not in first_lines:
        refuse(f"no PR comment or review opens with `Approved {head}`; launch the reviewer agent at this sha")


raw = sys.stdin.read()
if not re.search(r"merge|git|hookspath", QUOTING.sub("", raw), re.I):
    sys.exit(0)
try:
    payload = json.loads(raw)
    command = payload["tool_input"]["command"]
    if not isinstance(command, str):
        raise TypeError(f"command is {type(command).__name__}")
    cwd = payload.get("cwd")
    cwd = cwd if cwd and os.path.isdir(cwd) else None
except (ValueError, KeyError, TypeError) as err:
    refuse(f"could not read the payload ({type(err).__name__}: {err})")
text = without_heredocs(command)
try:
    commands = list(segments(text))
except ValueError:  # an unclosed quote
    commands = []
    if MENTION.search(QUOTING.sub("", text)):
        refuse("this command cannot be lexed and names `pr merge`; run `gh pr merge` on its own line")
try:
    readings = []
    for join in (True, False):
        try:
            readings.append(list(segments(command, join)))
        except ValueError:  # an unclosed quote: bash still runs every line before it
            readings.append(None)
    if None in readings and bypass_text(command) or \
            any(bypasses(words) for reading in readings if reading for words in reading):
        refuse("hook bypass refused: fix what the hook refused, or BLOCKED the owner")
    merges = []
    for words in commands:
        found = list(gh_merge(unredirected(words)))
        if len(found) != mentions(words):
            refuse("a `pr merge` in this command is not a command of its own; run `gh pr merge` on its own line, and write text naming it with a file tool")
        merges += found
except Exception as err:  # exit 1 would let the command run
    refuse(f"could not read the command ({type(err).__name__})")
for args in merges:
    check(args, cwd)
