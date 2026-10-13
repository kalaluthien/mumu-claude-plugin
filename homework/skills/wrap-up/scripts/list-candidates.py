#!/usr/bin/env python3
"""List a harvest's surprise candidates, one line each: time, kind, what.

  list-candidates.py [<transcript|session>]   the session in CLAUDE_CODE_SESSION_ID by default

The candidates are the work since the stop that ended the last wrap-up the hook
asked for: a failed tool result, a permission refusal, an AskUserQuestion
answer other than its `(Recommended)` option, a step redone (a commit amended,
reset or reverted, a force push, files restored), and each `FINDINGS:` or
`BLOCKED:` comment or review made then on an issue or pull request a `gh`
command named.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import transcript  # noqa: E402

REFUSAL = re.compile(r"Permission for this \w+ was denied|requires approval|doesn't want to proceed|hook error"
                     r"|<tool_use_error>Blocked|requested permissions|contains multiple operations")
REDO = re.compile(r"git\s+commit\b[^;&|\n]*--amend|git\s+(reset|revert|restore)\b|git\s+checkout\s+(?!-b\b)[^;&|\n]*\s--(\s|$)"
                  r"|git\s+push\b[^;&|\n]*(\s-f\b|--force)")
ISSUE_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)")
GH_NUMBER = re.compile(r"\bgh\s+(?:issue|pr)\s+\w+\s+(?:[^|;&\n]*?\s)?#?(\d+)\b")
GH_REPO = re.compile(r"(?:-R|--repo)[\s=]+([\w.-]+/[\w.-]+)|\bapi\s+(?:-\S+\s+)*repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)/(\d+)")
OPENS = re.compile(r"\s*(findings|blocked)\b:?", re.I)


def since_last_ask(entries):
    """Index after the stop that ended the wrap-up the last ask asked for, a running one aside."""
    asks = [i for i, e in enumerate(entries) if transcript.asked_at(e)]
    for ask in reversed(asks):
        later = [i for i in range(ask + 1, len(entries)) if transcript.is_stop(entries[i])]
        if later:
            return later[0] + 1
    return 0


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
        for use in transcript.blocks_of(entry, "tool_use"):
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
        for result in transcript.blocks_of(entry, "tool_result"):
            if re.search(r"\bgh\s+(?:issue|pr)\s+create\b", uses.get(result.get("tool_use_id"), "")):
                refs.update(ISSUE_URL.findall(transcript.text_of(result)))
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
            when = transcript.seconds({"timestamp": item.get(at)})
            found = OPENS.match(first)
            if found and when is not None and start <= when <= end:
                yield f"{item.get(at)} {found.group(1).lower()} {item.get('html_url')} {first[:80]}"


def candidates(entries):
    """One line per surprise since the last harvest: time, kind, what."""
    window = entries[since_last_ask(entries):]
    uses, lines = {}, []
    for entry in window:
        at = entry.get("timestamp", "")
        for use in transcript.blocks_of(entry, "tool_use"):
            uses[use.get("id")] = use
            command = str((use.get("input") or {}).get("command", ""))
            if use.get("name") == "Bash" and REDO.search(command):
                lines.append(f"{at} redo {command[:120]!r}")
        for result in transcript.blocks_of(entry, "tool_result"):
            use = uses.get(result.get("tool_use_id")) or {}
            if result.get("is_error"):
                kind = "refusal" if REFUSAL.search(transcript.text_of(result)) else "failure"
                lines.append(f"{at} {kind} {use.get('name', '?')}: {transcript.text_of(result)[:120]!r}")
            elif use.get("name") == "AskUserQuestion":
                lines += [f"{at} override {what}" for what in overrides(use, entry)]
    times = [t for t in map(transcript.seconds, window) if t is not None]
    if times:
        for repo, number in github_refs(window):
            lines += comments(repo, number, times[0], times[-1])
    return sorted(lines)


if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    path = transcript.find(session) if session else None
    entries = transcript.entries_of(path or "")
    if entries is None:
        print(f"no transcript: {session or 'CLAUDE_CODE_SESSION_ID names none'}", file=sys.stderr)
        sys.exit(1)
    found = candidates(entries)
    print("\n".join(found + [f"candidates: {len(found)}"]))
