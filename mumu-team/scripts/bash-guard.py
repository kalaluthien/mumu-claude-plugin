#!/usr/bin/env python3
"""PreToolUse hook on Bash: refuse a raw `gh pr merge`, since `merge.py` is the only merge path, and a git hook bypass,
even as text only naming either, which goes through a file and `--body-file`."""
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
    """Count `pr [-R <repo>]... merge` in the words, and in each word, which a shell could run."""
    count = 0
    for word in words:
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
    try:
        readings = [lexed(command), lexed(command, False)]  # None for an unclosed quote: bash still runs every line before it
        if readings[0] is None and MENTION.search(QUOTING.sub("", command)):
            refuse(RAW_MERGE)
        if None in readings and bypass_text(command) or \
                any(bypasses(words) for reading in readings if reading for words in reading):
            refuse("hook bypass refused: fix what the hook refused, or BLOCKED the owner")
        if any(mentions(words) for words in readings[0] or []):
            refuse(RAW_MERGE)
    except Exception as err:  # exit 1 would let the command run
        refuse(f"could not read the command ({type(err).__name__})")


if __name__ == "__main__":
    main()
