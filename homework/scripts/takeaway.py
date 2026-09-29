#!/usr/bin/env python3
"""Ask for a harvest of lessons, or a dream, before a session stops, in an armed repository.

  takeaway.py              the Stop hook: its payload on stdin, the plugin's
                           data directory in CLAUDE_PLUGIN_DATA
  takeaway.py arm <data>   arm the current directory's repository; a Bash
                           call does not inherit CLAUDE_PLUGIN_DATA
  takeaway.py candidates [<transcript>]
                           list a harvest's surprise candidates, the session's
                           own transcript by default

A harvest's candidates are the work since the stop that ended the last harvest
a block asked for, compactions included, since the transcript keeps every
entry: a failed tool result, a permission refusal, an AskUserQuestion answer
other than its `(Recommended)` option, a step redone (a commit amended, reset
or reverted, a force push, files restored), and each `FINDINGS:` or `BLOCKED:`
comment or review made then on an issue or pull request a `gh` command named.

The hook blocks with PROMPT only when the repository (its git common dir) is
armed, no transcript entry came from `claude -p` or the SDK, WORK_THRESHOLD
tool calls of any kind were made since the harvest its last block asked for,
and HARVEST_INTERVAL minutes passed since that block; else it exits silently.
So it asks once at 40 calls in a session, then again only after 40 more calls
and 120 min. Failures, refusals or pushback as a trigger reached few sessions
beyond it that later wrote a memory (replay-harvest-triggers.py, #217).

At a stop that asks no harvest, it blocks with DREAM_PROMPT once
DREAM_THRESHOLD memory files of the transcript's projects folder changed since
<data>/dreamed, touching that stamp when it asks and when the transcript shows
dream ran after it, so it asks again only once as many files change anew.
Changed memory files beat shell defects and elapsed days as the trigger
(replay-dream-triggers.py, #204).
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

WORK_THRESHOLD = int(os.environ.get("WORK_THRESHOLD", "40"))
HARVEST_INTERVAL = float(os.environ.get("HARVEST_INTERVAL", "120"))
DREAM_THRESHOLD = int(os.environ.get("DREAM_THRESHOLD", "5"))
PROMPT = "Before you stop, harvest this session's work with the retro skill."
DREAM_PROMPT = "Memory files changed since the last dream: run the dream skill before you stop."
REFUSAL = re.compile(r"Permission for this \w+ was denied|requires approval|doesn't want to proceed|hook error"
                     r"|<tool_use_error>Blocked|requested permissions|contains multiple operations")
REDO = re.compile(r"git\s+commit\b[^;&|\n]*--amend|git\s+(reset|revert|restore)\b|git\s+checkout\s+(?!-b\b)[^;&|\n]*\s--(\s|$)"
                  r"|git\s+push\b[^;&|\n]*(\s-f\b|--force)")
ISSUE_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)")
GH_NUMBER = re.compile(r"\bgh\s+(?:issue|pr)\s+\w+\s+(?:[^|;&\n]*?\s)?#?(\d+)\b")
GH_REPO = re.compile(r"(?:-R|--repo)[\s=]+([\w.-]+/[\w.-]+)|\bapi\s+(?:-\S+\s+)*repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)/(\d+)")
OPENS = re.compile(r"\s*(findings|blocked)\b:?", re.I)


def repo_key(cwd):
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return hashlib.sha256(os.path.realpath(out).encode()).hexdigest()[:16]


def is_block(entry):
    return (entry.get("type"), entry.get("subtype")) == ("system", "stop_hook_summary") and PROMPT in " ".join(entry.get("hookErrors") or [])


def blocks(entries):
    return [i for i, e in enumerate(entries) if is_block(e)]


def harvest_end(entries, block):
    """Index after the stop that ended the harvest block asked for, None while it runs."""
    later = [i for i in range(block + 1, len(entries)) if entries[i].get("subtype") == "stop_hook_summary"]
    return later[0] + 1 if later else None


def work_done(entries):
    """Tool calls after the stop that ended the harvest the last block asked for."""
    start = 0
    if blocks(entries):
        start = harvest_end(entries, blocks(entries)[-1]) or len(entries)
    return sum(1 for e in entries[start:] if e.get("type") == "assistant"
               for block in e["message"]["content"] if block.get("type") == "tool_use")


def seconds(entry):
    try:
        return datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def minutes_since_block(entries):
    at = seconds(entries[blocks(entries)[-1]]) if blocks(entries) else None
    return None if at is None else (datetime.now(timezone.utc).timestamp() - at) / 60


def dream_ran(entries, since):
    """Whether dream ran, typed or by the Skill tool, after since."""
    for entry in entries:
        body = (entry.get("message") or {}).get("content")
        text = body if isinstance(body, str) else json.dumps(body)
        if (seconds(entry) or 0) > since and (
                re.search(r"<command-name>/(homework:)?dream</command-name>", text)
                or re.search(r'"skill": "(homework:)?dream"', text)):
            return True
    return False


def memory_changed(projects, since):
    """Memory files, index aside, changed after since."""
    return sum(1 for path in glob.glob(os.path.join(glob.escape(projects), "*", "memory", "*.md"))
               if os.path.basename(path) != "MEMORY.md" and os.path.getmtime(path) > since)


def dream(data, transcript, entries):
    """Whether to ask for a dream; touches the stamp when it asks or dream ran."""
    stamp = os.path.join(data, "dreamed")
    if not os.path.exists(stamp):
        open(stamp, "w").close()
        return False
    since = os.path.getmtime(stamp)
    ask = memory_changed(os.path.dirname(os.path.dirname(transcript)), since) >= DREAM_THRESHOLD
    ran = dream_ran(entries, since)
    if ask or ran:
        os.utime(stamp)
    return ask and not ran


def entries_of(path):
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def blocks_of(entry, kind):
    body = (entry.get("message") or {}).get("content")
    return [b for b in body if b.get("type") == kind] if isinstance(body, list) else []


def text_of(block):
    body = block.get("content")
    return body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)


def since_last_harvest(entries):
    """Index after the stop that ended the last harvest a block asked for, a running one aside."""
    return max([end for end in (harvest_end(entries, b) for b in blocks(entries)) if end] or [0])


def overrides(use, result):
    """Questions whose answer is not their (Recommended) option."""
    answers = (result.get("toolUseResult") or {}).get("answers") or {}
    for question in (use.get("input") or {}).get("questions") or []:
        picks = [o.get("label", "") for o in question.get("options") or [] if "(Recommended)" in o.get("label", "")]
        answer = str(answers.get(question.get("question"), ""))
        if picks and answer and not any(pick in answer for pick in picks):
            yield f"{question.get('question', '')[:60]!r} -> {answer[:60]!r}"


def github_refs(window):
    """(repo, number) of each issue or pull request a gh command named, or a gh create printed."""
    uses, refs, bare, repos = {}, set(), [], []
    for entry in window:
        for use in blocks_of(entry, "tool_use"):
            command = str((use.get("input") or {}).get("command", ""))
            if use.get("name") == "Bash" and re.search(r"\bgh\s", command):
                uses[use.get("id")] = command
                refs.update(ISSUE_URL.findall(command))
                for found in GH_REPO.finditer(command):
                    repos.append(found.group(1) or found.group(2))
                    if found.group(3):
                        refs.add((found.group(2), found.group(3)))
                named = re.search(r"(?:-R|--repo)[\s=]+([\w.-]+/[\w.-]+)", command)
                bare += [(named.group(1) if named else None, n) for n in GH_NUMBER.findall(command)]
        for result in blocks_of(entry, "tool_result"):
            if re.search(r"\bgh\s+(?:issue|pr)\s+create\b", uses.get(result.get("tool_use_id"), "")):
                refs.update(ISSUE_URL.findall(text_of(result)))
    repos += [repo for repo, _ in refs]
    default = max(set(repos), key=repos.count) if repos else None
    refs.update((repo or default, n) for repo, n in bare if repo or default)
    return sorted(refs)


def comments(repo, number, start, end):
    """FINDINGS: and BLOCKED: comments and reviews on one issue or pull request made in [start, end]."""
    for path, at in ((f"repos/{repo}/issues/{number}/comments", "created_at"),
                     (f"repos/{repo}/pulls/{number}/reviews", "submitted_at")):
        run = subprocess.run(["gh", "api", "--paginate", path, "--jq", ".[] | @json"], capture_output=True, text=True)
        for item in [] if run.returncode else map(json.loads, run.stdout.splitlines()):
            first = ((item.get("body") or "").strip().splitlines() or [""])[0]
            when = seconds({"timestamp": item.get(at)})
            found = OPENS.match(first)
            if found and when is not None and start <= when <= end:
                yield f"{item.get(at)} {found.group(1).lower()} {item.get('html_url')} {first[:80]}"


def candidates(entries):
    """One line per surprise since the last harvest: time, kind, what."""
    window = entries[since_last_harvest(entries):]
    uses, lines = {}, []
    for entry in window:
        at = entry.get("timestamp", "")
        for use in blocks_of(entry, "tool_use"):
            uses[use.get("id")] = use
            command = str((use.get("input") or {}).get("command", ""))
            if use.get("name") == "Bash" and REDO.search(command):
                lines.append(f"{at} redo {command[:120]!r}")
        for result in blocks_of(entry, "tool_result"):
            use = uses.get(result.get("tool_use_id")) or {}
            if result.get("is_error"):
                kind = "refusal" if REFUSAL.search(text_of(result)) else "failure"
                lines.append(f"{at} {kind} {use.get('name', '?')}: {text_of(result)[:120]!r}")
            elif use.get("name") == "AskUserQuestion":
                lines += [f"{at} override {what}" for what in overrides(use, entry)]
    times = [t for t in map(seconds, window) if t is not None]
    if times:
        for repo, number in github_refs(window):
            lines += comments(repo, number, times[0], times[-1])
    return sorted(lines)


def own_transcript():
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    found = glob.glob(os.path.join(glob.escape(root), "projects", "*",
                                   f"{os.environ.get('CLAUDE_CODE_SESSION_ID', '-')}.jsonl"))
    return found[0] if found else None


def arm(data):
    key = repo_key(os.getcwd())
    if key is None:
        print(f"not armed: {os.getcwd()} is not inside a git repository", file=sys.stderr)
        return 1
    path = os.path.join(data, "armed", key)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(os.getcwd() + "\n")
    except OSError as error:
        print(f"not armed: {error}", file=sys.stderr)
        return 1
    print(f"armed {os.getcwd()} at {path}")
    return 0


def hook():
    payload = json.load(sys.stdin)
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    key = repo_key(payload.get("cwd") or os.getcwd())
    if not data or key is None or not os.path.exists(os.path.join(data, "armed", key)):
        return 0
    entries = entries_of(payload.get("transcript_path") or "")
    if entries is None or any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
        return 0
    since = minutes_since_block(entries)
    if (since is None or since >= HARVEST_INTERVAL) and work_done(entries) >= WORK_THRESHOLD:
        json.dump({"decision": "block", "reason": PROMPT}, sys.stdout)
    elif dream(data, payload.get("transcript_path"), entries):
        json.dump({"decision": "block", "reason": DREAM_PROMPT}, sys.stdout)
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["arm"]:
        if len(sys.argv) == 3:
            sys.exit(arm(sys.argv[2]))
        print("usage: takeaway.py arm <plugin data directory>", file=sys.stderr)
        sys.exit(2)
    if sys.argv[1:2] == ["candidates"]:
        path = sys.argv[2] if len(sys.argv) > 2 else own_transcript()
        entries = entries_of(path or "")
        if entries is None:
            print(f"no transcript: {path or 'CLAUDE_CODE_SESSION_ID names none'}", file=sys.stderr)
            sys.exit(1)
        found = candidates(entries)
        print("\n".join(found + [f"candidates: {len(found)}"]))
        sys.exit(0)
    sys.exit(hook())
