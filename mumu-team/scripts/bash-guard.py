#!/usr/bin/env python3
"""PreToolUse hook on Bash: refuse a raw `gh pr merge`, since `merge.py` is the only merge path, and a git hook bypass.

The command is split as a shell would, and each word a shell could run is read
inside too; text only naming a merge or a bypass passes: a heredoc body a text
reader reads, a message or body flag, a `grep` pattern. A payload that cannot be
read is refused (exit 2).
"""
import json
import os
import re
import shlex
import sys

SEPARATORS = set(";&|()\n")
DESCRIPTOR = re.compile(r"(^|[\s;&|()])(?:\d+|\{\w+\})(?=[<>])")
QUOTING = re.compile(r"[\"'\\]")
MENTION = re.compile(r"\bpr\b[\s\S]*?\bmerge\b")
PR_MERGE = re.compile(r"(?:^|\0)pr(?:\0(?:-R|--repo)\0[^\0]*|\0--repo=[^\0]*)*\0merge(?=\0|$)")  # words joined by NUL
HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][\w.-]*)\2")
RUNS = re.compile(r"\$\(|`")
WORD = re.compile(r"[^\s;&|()<>`'\"]+")
ASSIGNMENT = re.compile(r"\w+=")
READERS = {"cat": None, "tee": None, "gh": {"issue", "pr", "release"}}  # builtins no alias can shadow; git may open an editor set lines before
EDITOR = re.compile(r"-[^-]*e|--edit")  # `-e`, `-eb`, `--edit`, `--editor`
TEXT_COMMANDS = {"grep", "egrep", "fgrep", "rg"}  # each reads its quoted words as text
PAGER = re.compile(r"-[^-]*O|--op")  # `git grep -O<cmd>`, `-iO`, `--open-files-in-pager=<cmd>`
IN_PLACE = re.compile(r"-[A-Za-z]*i|--in-place")  # `sed -i ''`, `-i.bak`, `-Ei`
SED_RUNS = re.compile(r"(?<![A-Za-z])[ewW](?![\w.-])|/[gpIiMm0-9]*[ewW][gpIiMm0-9]*(?![\w./-])")  # an `e`, `w` or `W` command or `s///` flag
SED_EXPRESSION = re.compile(r"^(-[A-Za-z]*?e|--expression=)")  # `-ne'e cmd'` is the script `e cmd`
TEXT_FLAGS = {"-b", "--body", "-t", "--title", "--comment", "--notes"}  # of gh
HOOKS_PATH = re.compile(r"^(['\"]?|--config-env=|GIT_CONFIG_KEY_\d+=['\"]?)core\.hookspath(['\"]?=|['\"]?$)", re.I)  # `-c k=v`, `'k'=v`, `--config-env=k=V`, `KEY_0=k`
HOOKS_PATH_TEXT = re.compile(r"(-c\s*|--config-env=|key_\d+=)core\.hookspath\b|\bconfig\b(?![^;&|\n]*\bget\b)[^;&|\n]*core\.hookspath[ \t]+[^\s;&|]")


RAW_MERGE = "a raw `pr merge` is refused; run `merge.py <pr-url>` in a Bash call of its own, and write text naming the merge with a file tool"


def refuse(reason):
    print(f"bash-guard: {reason}", file=sys.stderr)
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


def lexed(text, join=True):
    """The word lists of text's commands, or None when a quote is unclosed."""
    try:
        return list(segments(text, join))
    except ValueError:
        return None


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
            heads.append(WORD.findall(line, j))  # an env prefix too, which no reader has
            start = bool(ASSIGNMENT.match(word))
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
            if piped or not all(map(reader, heads)) or not opener[2] and RUNS.search("\n".join(body)):
                kept += body
            i = end + 1
    return "\n".join(kept)


def reader(words):
    """Whether the command in words, from its first word, reads text only as text: `cat`, `tee`, or a builtin `gh` subcommand, with no env prefix (`GH_EDITOR=sh`) and no editor flag."""
    head = os.path.basename(words[0]) if words else ""
    return head in READERS and (READERS[head] is None or words[1:2] and words[1] in READERS[head]) \
        and not any(EDITOR.match(w) for w in words)


def text_word(words, i):
    """Whether words[i] is only text: a `grep` pattern, a `git grep` word with no pager flag (`-O`), a `sed -i` word when no
    script word runs (`e`) or writes (`w`) a command, or a message or body flag's value of a reader."""
    bare = [w for w in words if not ASSIGNMENT.match(w)]
    head, rest = (os.path.basename(bare[0]), bare[1:]) if bare else ("", [])
    if RUNS.search(words[i]) or head in ("git", "sed") and ASSIGNMENT.match(words[i]):  # `GIT_PAGER=...` runs
        return False
    if head == "git" and rest[:1] == ["grep"]:
        return not any(PAGER.match(w) for w in rest[1:])
    if head == "sed" and any(IN_PLACE.match(w) for w in rest):
        return not any(SED_RUNS.search(SED_EXPRESSION.sub("", w)) for w in rest)
    return head in TEXT_COMMANDS or reader(words) and \
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
        inner = lexed(word)
        if inner is None:  # an unclosed quote
            count += len(MENTION.findall(word))
            continue
        if inner != [[word]] and set(word) - set(";&|()<>"):  # a word that splits is text a shell could run
            count += sum(mentions(words) for words in inner)
    return count + len(PR_MERGE.findall("\0".join(QUOTING.sub("", word).strip() for word in unredirected(words))))


def bypasses(words):
    """Whether the words skip a git hook: `--no-verify` or its abbreviation, `git commit -n`, or setting `core.hooksPath`."""
    words = unredirected(words)
    for i, word in enumerate(words):
        for join in (True, False):  # `\` then a newline joins lines, unless the `\` is escaped or in a comment
            inner = lexed(word, join) or [[word]]  # an apostrophe in a message does not lex
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


def main():
    raw = sys.stdin.read()
    if not re.search(r"merge|git|hookspath", QUOTING.sub("", raw), re.I):
        sys.exit(0)
    try:
        payload = json.loads(raw)
        command = payload["tool_input"]["command"]
        if not isinstance(command, str):
            raise TypeError(f"command is {type(command).__name__}")
    except (ValueError, KeyError, TypeError) as err:
        refuse(f"could not read the payload ({type(err).__name__}: {err})")
    text = without_heredocs(command)
    try:
        readings = [lexed(text), lexed(text, False)]  # None for an unclosed quote: bash still runs every line before it
        if readings[0] is None and MENTION.search(QUOTING.sub("", text)):
            refuse(RAW_MERGE)
        if None in readings and bypass_text(text) or \
                any(bypasses(words) for reading in readings if reading for words in reading):
            refuse("hook bypass refused: fix what the hook refused, or BLOCKED the owner")
        if any(mentions(words) for words in readings[0] or []):
            refuse(RAW_MERGE)
    except Exception as err:  # exit 1 would let the command run
        refuse(f"could not read the command ({type(err).__name__})")


if __name__ == "__main__":
    main()
