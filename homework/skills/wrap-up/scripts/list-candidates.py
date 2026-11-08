#!/usr/bin/env python3
"""List a retro's surprise candidates, one line each: time, kind, what.

usage: list-candidates.py [<transcript|session>]   the session in CLAUDE_CODE_SESSION_ID by default

The candidates are the work since the stop that ended the last wrap-up the hook
asked for: a failed tool result, a permission refusal, an AskUserQuestion
answer other than its recommended option, a step redone (a commit amended,
reset or reverted, a force push, files restored), each message the owner typed,
each hook block or added context, collapsed by text with its count, and each
record the session wrote that opens with a capital keyword and a colon. It
reads only the transcript; secrets are masked.
"""
import os
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import transcript  # noqa: E402

REFUSAL = re.compile(r"Permission for this \w+ was denied|requires approval|doesn't want to proceed|hook error"
                     r"|<tool_use_error>Blocked|requested permissions|contains multiple operations")
REDO = re.compile(r"git\s+commit\b[^;&|\n]*--amend|git\s+(reset|revert|restore)\b|git\s+checkout\s+(?!-b\b)[^;&|\n]*\s--(\s|$)"
                  r"|git\s+push\b[^;&|\n]*(\s-f\b|--force)")
RECOMMENDED = ("(Recommended)", "(추천)", "(권장)")
# typed text the owner did not word: a launch prompt, a slash command, or another session's text typed in,
# which opens with its session name and a colon or with a record's keyword and a colon or url
LAUNCH = re.compile(r"\s*(Run the [\w:.-]+ skill\b|<command-(name|message)>|<local-command-|(From )?[a-z0-9]+(-[a-z0-9]+)+: "
                    r"|[A-Z]{4,}(:| on \S))|[\s\S]*\byour session name is\b")
PASTED = re.compile(r"<pasted_content\b[^>]*>[\s\S]*?(</pasted_content[^>]*>|$)")
RECORD = re.compile(r"\s*([A-Z]{4,}): (\S.*)")
# the body a command posts: a quoted string after a body, message or comment flag, or a here-document's first line
POSTED = re.compile(r"(?:--body|--message|--comment|-[bm])[\s=]+(?:\"\s*([A-Z]{4,}): ([^\"\n\\]+)|'\s*([A-Z]{4,}): ([^'\n]+))"
                    r"|<<-?\s*[\"']?\w+[\"']?[^\n]*\n\s*([A-Z]{4,}): ([^\n]+)")
# no word boundary before a prefix, since a token glued to Hangul has none
SECRET = re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_\w{20,}|glpat-[\w-]{20,}|npm_[A-Za-z0-9]{30,}"
                    r"|sk-[\w-]{20,}|sk_(?:live|test)_\w{16,}|AKIA[0-9A-Z]{16}|AIza[\w-]{35}|xox[abprs]-[\w-]{10,}"
                    r"|eyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"
                    r"|(?i:bearer\s+|authorization:\s*\w+\s+)[\w.~+/-]{8,}=*|(?<![\w.-])[\w.-]+:[^/\s@:]+(?=@[\w-])"
                    r"|(?i:--?[\w-]*(?:password|passwd|secret|api[_-]?key|token)[\w-]*[\s=]+"
                    r"|[\w-]*(?:password|passwd|secret|api[_-]?key|token)[\w-]*[\"']?\s*[=:]\s*[\"']?)[^\s\"',}]+")
OWNER_CAP = 20
HOOK_CAP = 10
WIDTH = 120


def masked(text):
    return SECRET.sub("<secret>", text)


def since_last_ask(entries):
    """Index after the stop that ended the wrap-up the last ask asked for, a running one aside."""
    asks = [i for i, e in enumerate(entries) if transcript.asked_at(e)]
    for ask in reversed(asks):
        after = next((i for i in range(ask + 1, len(entries)) if transcript.is_stop(entries[i])), None)
        if after is not None:
            return after + 1
    return 0


def overrides(use, result):
    """Questions whose answer is not their recommended option."""
    answers = (result.get("toolUseResult") or {}).get("answers") or {}
    for question in (use.get("input") or {}).get("questions") or []:
        picks = [label for label in (option.get("label", "") for option in question.get("options") or [])
                 if any(mark in label for mark in RECOMMENDED)]
        stems = {label for pick in picks for label in (pick, *(pick.replace(mark, "").strip() for mark in RECOMMENDED))}
        answer = str(answers.get(question.get("question"), ""))
        if picks and answer and not stems & ({part.strip() for part in answer.split(",")} | {answer.strip()}):
            yield f"{masked(question.get('question', ''))[:60]!r} -> {masked(answer)[:60]!r}"


def owner_text(entry):
    """The text the owner typed in this entry, or None for any other source."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    if (entry.get("origin") or {}).get("kind") != "human":
        return None
    body = (entry.get("message") or {}).get("content")
    text = body if isinstance(body, str) else " ".join(b.get("text", "") for b in transcript.blocks_of(entry, "text"))
    text = PASTED.sub(" ", text)
    return None if not text.strip() or LAUNCH.match(text) else text


def hook_text(entry):
    """The text a hook blocked with or added, or None."""
    attachment = entry.get("attachment") or {}
    kind = attachment.get("type")
    if kind == "hook_blocking_error":
        found = attachment.get("blockingError")
        return str(found.get("blockingError", "") if isinstance(found, dict) else found or "")
    if kind == "hook_additional_context":
        content = attachment.get("content")
        return " ".join(map(str, content)) if isinstance(content, list) else str(content or "")
    return None


def written_texts(use):
    """The first line of a file the session wrote or a message it sent; a command's text is left out, since a probe's sample records would show."""
    given = use.get("input") or {}
    return [str(given[key]).lstrip().split("\n", 1)[0] for key in ("content", "message") if given.get(key)]


def candidates(entries):
    """One line per surprise since the last retro: time, kind, what."""
    window = entries[since_last_ask(entries):]
    uses, lines, owner, hooks, records = {}, [], [], Counter(), {}
    for entry in window:
        at = entry.get("timestamp", "")
        said = owner_text(entry)
        if said is not None:
            owner.append(f"{at} owner {masked(' '.join(said.split()))[:WIDTH * 2]!r}")
        heard = hook_text(entry)
        if heard and not heard.lstrip().startswith(transcript.SIGNAL):
            hooks[masked(" ".join(heard.split()))[:WIDTH]] += 1
        for use in transcript.blocks_of(entry, "tool_use"):
            uses[use.get("id")] = use
            command = str((use.get("input") or {}).get("command", ""))
            if use.get("name") == "Bash" and REDO.search(command):
                lines.append(f"{at} redo {masked(command)[:WIDTH]!r}")
            found = [RECORD.match(text) for text in written_texts(use)] + list(POSTED.finditer(command))
            for record in filter(None, found):
                keyword, body = [part for part in record.groups() if part][:2]
                records.setdefault(f"{keyword}: {masked(body.strip())[:WIDTH]}", at)
        for result in transcript.blocks_of(entry, "tool_result"):
            use = uses.get(result.get("tool_use_id")) or {}
            if result.get("is_error"):
                text = transcript.text_of(result)
                kind = "refusal" if REFUSAL.search(text) else "failure"
                lines.append(f"{at} {kind} {use.get('name', '?')}: {masked(text)[:WIDTH]!r}")
            elif use.get("name") == "AskUserQuestion":
                lines += [f"{at} override {what}" for what in overrides(use, entry)]
    lines += owner[-OWNER_CAP:]
    if len(owner) > OWNER_CAP:
        lines.append(f"{owner[0].split()[0]} owner-dropped {len(owner) - OWNER_CAP} older owner messages past the cap")
    lines += [f"{at} record {what!r}" for what, at in records.items()]
    lines = sorted(lines)
    lines += [f"hook x{n} {text!r}" for text, n in hooks.most_common(HOOK_CAP)]
    if len(hooks) > HOOK_CAP:
        lines.append(f"hook-dropped {len(hooks) - HOOK_CAP} rarer hook texts past the cap")
    return lines


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    session = args[0] if args else os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    path = transcript.find(session) if session else None
    entries = transcript.entries_of(path or "")
    if entries is None:
        print(f"no transcript: {session or 'CLAUDE_CODE_SESSION_ID names none'}", file=sys.stderr)
        return 1
    found = candidates(entries)
    print("\n".join(found + [f"candidates: {len(found)}"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
