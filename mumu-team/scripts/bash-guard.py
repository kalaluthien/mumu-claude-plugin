#!/usr/bin/env python3
"""PreToolUse hook on Bash: refuse a raw `gh pr merge`, since `merge.py` is the only merge path, and a git hook bypass,
even as text only naming either, which goes through a file and `--body-file`; and in a lead's or worker's session, what
the kickoff skill gives another role: `APPROVED:` and `FINDINGS:` the reviewer's, `DECIDED:` the lead's through
`decide.py`, a task's body, labels, reopening and stop its lead's, and no title over 40 characters."""
import json
import os
import pathlib
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
ROLES = {"mumu-team:lead": "lead", "mumu-team:worker": "worker"}
GH_WRITE = re.compile(r"\bgh\s+(?:(?:-R|--repo)[=\s]\S+\s+)*(issue|pr)\s+(comment|review|create|edit|close|reopen)\b")
KEYWORD = re.compile(r"\s*(approved|findings|decided)\b", re.I)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n([^\n]*)")
TITLE = 40
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


def option(words, *flags):
    """The value of the first of `flags` in `words`, as `--flag v`, `--flag=v` or `-f v`, else None."""
    for i, word in enumerate(words):
        for flag in flags:
            if word == flag and i + 1 < len(words):
                return words[i + 1]
            if flag.startswith("--") and word.startswith(flag + "="):
                return word[len(flag) + 1:]
    return None


def writes(command, cwd):
    """(`issue` or `pr`, its verb, its words, the first line of each text it writes) for each `gh issue|pr <verb>` in
    `command`: its `--body`, its `--body-file` read from `cwd`, or a heredoc opened on its line."""
    found = []
    for m in GH_WRITE.finditer(command):
        end = command.find("\n", m.start())
        line = command[m.start():end if end >= 0 else len(command)]
        words = (lexed(line) or [line.split()] or [[]])[0]
        texts = [t for t in (option(words, "--body", "-b"),) if t is not None]
        path = option(words, "--body-file", "-F")
        if path and path != "-":
            try:
                texts.append((pathlib.Path(cwd) / path).read_text())
            except OSError:
                pass
        doc = HEREDOC.search(command, m.start())
        if doc and doc.start() < m.start() + len(line):
            texts.append(doc[3])
        found.append((m[1], m[2], words, [(t.strip().splitlines() or [""])[0] for t in texts]))
    return found


def role_refusal(command, role, cwd):
    """What `command` does that the kickoff skill gives another role than `role`, a lead or a worker, else None."""
    if role == "worker" and any(os.path.basename(w) == "decide.py" for words in lexed(command) or [] for w in words):
        return "`DECIDED:` and `decide.py` are the lead's: post `BLOCKED: <question>` and prompt your lead"
    for kind, verb, words, lines in writes(command, cwd):
        for line in lines:
            m = KEYWORD.match(line)
            if m and m[1].lower() in ("approved", "findings"):
                return f"`{m[1].upper()}:` is the reviewer's alone: launch the `reviewer` agent to post it"
            if m and verb in ("comment", "review"):
                return "`DECIDED:` goes through `decide.py <url> < <decision>`, the lead's"
        title = option(words, "--title", "-t")
        if verb in ("create", "edit") and title is not None and len(title) > TITLE:
            return f"a title is at most {TITLE} characters, verb first; this one has {len(title)}"
        stop = verb == "close" and (option(words, "--reason", "-r") or "").replace("_", " ").lower() == "not planned"
        if role == "worker" and kind == "issue" and (verb in ("edit", "reopen") or stop):
            return "a task's body, labels, reopening and stop are its lead's: post `BLOCKED: <question>` and prompt your lead"
    return None


def main():
    raw = sys.stdin.read()
    if not re.search(r"merge|git|hookspath|gh|decide", QUOTING.sub("", raw), re.I):
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
        role = ROLES.get(payload.get("agent_type"))
        if role and (why := role_refusal(command, role, payload.get("cwd") or ".")):
            refuse(why)
    except Exception as err:  # exit 1 would let the command run
        refuse(f"could not read the command ({type(err).__name__})")


if __name__ == "__main__":
    main()
