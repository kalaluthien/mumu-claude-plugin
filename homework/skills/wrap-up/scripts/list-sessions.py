#!/usr/bin/env python3
"""Map a window of sessions for the dream: write digests for the haiku facet agents, and tool-failure signatures.

usage: list-sessions.py due <data> [--due-hours <h>]                  `due` when <data>/last-map is <h> hours old or missing, else `not due`;
                                                                       <h> by <data>'s name as homework/lib/stamp.py sets it
       list-sessions.py map <data> [--window-days <d>] [--limit <n>]  every in-window session: signatures to <data>/stats/; the newest
                                                                       <n> (40) without a facet: digests to <data>/digests/; touches <data>/last-map
       list-sessions.py digest <data> <path>...                       digests and signatures of the named transcripts, window and
                                                                       limit aside

Digests print as `batch <k>: <digest> ...` lines of at most 10, one haiku agent each. The window is the interactive
top-level transcripts under ${CLAUDE_CONFIG_DIR:-~/.claude}/projects changed in the last <d> days (14). A session with no
owner line after its first prompt and no answer gets no digest, since a friction or habit item answers what the agent did,
and such a session, often one another session started, shows none. A Bash `ls` of the very path an `rm` or `rmdir` of the same command removed,
or an `ls` whose exit status the command reads (`|| …`, `; echo $?`), expects the path missing, so its error line is no failure signature. An `AskUserQuestion` answer shows as
`[ANSWER L<n>]: <question> | options: <label> / ... | answer: <the owner's pick or own words>`.
"""
import glob
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import claude_config  # noqa: E402
import credentials  # noqa: E402
import stamp  # noqa: E402
import transcript  # noqa: E402

WINDOW_DAYS, PER_RUN, PER_BATCH = 14, 40, 10
FLAGS = {"--window-days": "days", "--due-hours": "hours", "--limit": "limit"}
VERB_FLAGS = {"due": {"--due-hours"}, "map": {"--window-days", "--limit"}, "digest": set()}
OWNER_CAP, AGENT_CAP, DIGEST_CAP = 500, 300, 30000
TAGS = re.compile(r"<(system-reminder|task-notification)>.*?</\1>", re.S)
# urls before paths, so a url is masked whole
VARIABLE = [(re.compile(pattern), replacement) for pattern, replacement in [
    (r"https?://\S+", "<url>"), (r"/[\w.~@%+-]+(?:/[\w.~@%+-]+)+", "<path>"), (r"\b[0-9a-f]{7,40}\b", "<hash>"),
    (r"(['\"`]).*?\1", "<q>"), (r"\d+", "<n>"), (r"\s+", " ")]]
NOISE = re.compile(r"^(Exit code <n>|<n>|-+|ok\b.*|This hook comes from .*)$")
DENIED = re.compile(r"doesn't want to proceed|user denied|rejected by the user", re.I)
REASON = re.compile(r"\[[A-Z][A-Za-z /-]+\]")
MISSING = re.compile(r"^ls: (.*): No such file or directory$", re.M)
STATEMENT = re.compile(r"&&|\|\||[;&|\n]")
# `ls <path> || …` or `ls <path>; echo $?` reads the exit status, so the ls expects its own failure
EXPECTS_MISSING = re.compile(r"\bls\b(?:[^;\n&|]|2>&1)*(?:\|\||;\s*echo \$\?)")


def repo_of(path):
    """The project folder's name, a worktree folded into its repository."""
    return re.sub(r"--claude-worktrees-.*$", "", os.path.basename(os.path.dirname(path)))


def window(now, days):
    """Top-level transcripts changed within the window, newest first."""
    paths = glob.glob(os.path.join(glob.escape(str(claude_config.folder())), "projects", "*", "*.jsonl"))
    recent = [path for path in paths if os.path.getmtime(path) >= now - days * 86400]
    return sorted(recent, key=os.path.getmtime, reverse=True)


def removed_paths(command):
    """Paths an `rm` or `rmdir` of the command names, as written."""
    paths = []
    for statement in STATEMENT.split(command):
        words = statement.split()
        if words[:1] in (["rm"], ["rmdir"]):
            paths += [word.strip("'\"") for word in words[1:] if word.strip("'\"") and not word.startswith("-")]
    return paths


def drop_expected_missing(command, text):
    """TEXT without the `ls` lines a Bash command expects: of a path it just removed, or one whose exit status it reads."""
    if EXPECTS_MISSING.search(command):
        return MISSING.sub("", text)
    removed = [path.replace("~", "", 1) if path.startswith("~") else path for path in removed_paths(command)]
    # a whole trailing path component, so a removed `a` never hides `/x/data`
    return MISSING.sub(lambda found: "" if any(found[1] == path or found[1].endswith("/" + path.strip("/")) for path in removed) else found[0], text)


def signature(tool, text, command=""):
    """The tool and the last meaningful error line, variable parts masked; None for a bare exit code, a denial or a missing path a Bash call expects."""
    if DENIED.search(text):
        return None
    if tool == "Bash":
        text = drop_expected_missing(command, text)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        for pattern, mask in VARIABLE:
            line = pattern.sub(mask, line)
        if line and not NOISE.match(line):
            lines.append(line)
    reason = REASON.search(text)
    return f"{tool}: {lines[-1][:100]}" + (f" {reason.group(0)}" if reason else "") if lines else None


def answer_lines(result, number):
    """One `[ANSWER L<n>]` line per question an `AskUserQuestion` result answered."""
    answers, notes = result.get("answers") or {}, result.get("annotations") or {}
    lines = []
    for question in result.get("questions") or []:
        asked = question.get("question", "")
        if asked not in answers:
            continue
        labels = " / ".join(str(option.get("label", "")) for option in question.get("options") or [])
        note = (notes.get(asked) or {}).get("notes") if isinstance(notes.get(asked), dict) else None
        text = f"{asked[:OWNER_CAP]} | options: {labels} | answer: {str(answers[asked])[:OWNER_CAP]}"
        lines.append(f"[ANSWER L{number}]: {text}" + (f" | note: {str(note)[:OWNER_CAP]}" if note else ""))
    return lines


def read(path):
    """(stats, lines, owners) of a transcript, stats None for an sdk session; lines are the digest's lines."""
    entries = transcript.entries_of(path) or []
    if any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
        return None, [], []
    uses, failures, lines, owners, end = {}, [], [], [], None
    for number, entry in enumerate(entries, 1):
        end = transcript.seconds(entry.get("timestamp")) or end
        if entry.get("isSidechain"):
            continue
        for block in transcript.blocks_of(entry, "tool_use"):
            uses[block.get("id")] = (block.get("name"), str((block.get("input") or {}).get("command", "")))
            lines.append(f"[Tool: {block.get('name')}]")
        if isinstance(entry.get("toolUseResult"), dict) and "answers" in entry["toolUseResult"]:
            answered = answer_lines(entry["toolUseResult"], number)
            owners += [{"line": number, "text": line} for line in answered]
            lines += answered
        for block in transcript.blocks_of(entry, "tool_result"):
            tool, command = uses.get(block.get("tool_use_id"), ("?", ""))
            key = block.get("is_error") and signature(tool, transcript.text_of(block), command)
            if key:
                failures.append({"key": key, "line": number, "time": transcript.seconds(entry.get("timestamp"))})
        if entry.get("type") == "assistant":
            for block in transcript.blocks_of(entry, "text"):
                if block.get("text", "").strip():
                    lines.append(f"[Agent L{number}]: {block['text'].strip()[:AGENT_CAP]}")
        elif entry.get("type") == "user" and (entry.get("origin") or {}).get("kind") == "human":
            body = (entry.get("message") or {}).get("content")
            texts = [body] if isinstance(body, str) else [block.get("text", "") for block in transcript.blocks_of(entry, "text")]
            for text in texts:
                text = TAGS.sub("", text).strip()
                if text and not text.startswith("[Request interrupted"):
                    owners.append({"line": number, "text": text})
                    lines.append(f"[OWNER L{number}]: {text[:OWNER_CAP]}")
    stats = {"path": path, "repo": repo_of(path), "end": end, "failures": failures}
    return stats, lines, owners


def digest(path, lines):
    """The insights cut when it fits; else every owner line with the agent text before it, oldest middle cut."""
    head = f"Session: {os.path.basename(path)[:-6]}\nProject: {repo_of(path)}\n"
    text = head + "\n".join(lines)
    if len(text) <= DIGEST_CAP:
        return text
    keep = []
    for k, line in enumerate(lines):
        if line.startswith(("[OWNER", "[ANSWER")):
            before = next((lines[index] for index in range(k - 1, -1, -1) if not lines[index].startswith("[Tool")), "")
            if before.startswith("[Agent") and (not keep or keep[-1] != before):
                keep.append(before)
            keep.append(line)
    body = "\n".join(keep)
    room = DIGEST_CAP - len(head) - 30
    return head + ("[oldest middle cut]\n" + body[-room:] if len(body) > room else body)


def private(target):
    """Open target for writing as 0600; chmod too, since an existing file keeps its old mode."""
    handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(handle, 0o600)
    return open(handle, "w", encoding="utf-8")


def write(data, path, kind, value):
    # digests hold the owner's words; makedirs(exist_ok=True) keeps an old folder's mode, so chmod each
    folder = os.path.join(data, kind)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(data, 0o700)
    os.chmod(folder, 0o700)
    target = os.path.join(folder, os.path.basename(path)[:-6] + (".txt" if kind == "digests" else ".json"))
    with private(target) as out:
        out.write(credentials.TOKEN.sub("<token>", value) if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return target


def batches(digests):
    for k in range(0, len(digests), PER_BATCH):
        print(f"batch {k // PER_BATCH + 1}: {' '.join(digests[k:k + PER_BATCH])}")


def options(verb, args):
    """(paths, settings) of the words after <data>, or None when a flag is not the verb's or lacks a number."""
    settings, paths, k = {"days": WINDOW_DAYS, "hours": None, "limit": PER_RUN}, [], 0
    while k < len(args):
        if args[k].startswith("--"):
            if args[k] not in VERB_FLAGS.get(verb, ()) or k + 1 >= len(args) or not re.fullmatch(r"[0-9]+", args[k + 1]):
                return None
            settings[FLAGS[args[k]]] = int(args[k + 1])
            k += 2
        else:
            paths.append(args[k])
            k += 1
    return paths, settings


def main(args):
    parsed = options(args[0], args[2:]) if len(args) >= 2 else None
    if parsed is None or args[0] not in VERB_FLAGS or bool(parsed[0]) != (args[0] == "digest"):
        print(__doc__, file=sys.stderr)
        return 2
    (named, settings), verb, data, now = parsed, args[0], args[1], time.time()
    if verb == "due":
        print("due" if stamp.due(data, settings["hours"]) else "not due")
        return 0
    paths = named if verb == "digest" else window(now, settings["days"])
    faceted = {os.path.basename(path)[:-5] for path in glob.glob(os.path.join(glob.escape(data), "facets", "*.json"))}
    digests, waiting = [], 0
    for path in paths:
        stats, lines, owners = read(path)
        if stats is None:
            continue
        write(data, path, "stats", stats)
        answered = any(owner["text"].startswith("[ANSWER") for owner in owners)
        if (len(owners) < 2 and not answered) or (os.path.basename(path)[:-6] in faceted and verb == "map"):
            continue
        if len(digests) < settings["limit"] or verb == "digest":
            digests.append(write(data, path, "digests", digest(path, lines)))
        else:
            waiting += 1
    if verb == "map":
        os.makedirs(data, mode=0o700, exist_ok=True)
        private(os.path.join(data, "last-map")).close()
        print(f"{len(digests)} sessions to facet; {waiting} wait for later runs")
    batches(digests)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
