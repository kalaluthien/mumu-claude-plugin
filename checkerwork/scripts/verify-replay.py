#!/usr/bin/env python3
"""Replay Claude Code session transcripts against the verify hook's two rules (task #394).

Usage: verify-replay.py <session-name>... [--projects <dir>]   (default dir ~/.claude/projects)

Per session, from the transcript `<dir>/*-<session-name>/*.jsonl`:
- main: `verify.sh` Bash runs, and hook refusals (a tool result or Stop feedback that says the hook "did not wait" or
  "verify.sh fails"), a refusal tied by tool_use_id to a `git commit` call counting as a commit's, else as a Stop's;
- new rule: the Stop asks for nothing, a commit asks for at most one run on a tree not passed, and can meet a refusal only
  where main's commit was refused. A transcript holds no tree ids, so every commit is counted as a tree not passed: an upper bound.
A session with no transcript prints that it cannot tell; one with no commit call yet is asked for nothing.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from fit import COMMIT  # noqa: E402

REFUSED = re.compile(r"did not wait|verify\.sh fails")
RUN = re.compile(r"(^|[\s/])verify\.sh\b")
NOT_A_RUN = {"grep", "cat", "ls", "sed", "head", "tail", "git", "echo", "rg", "read", "wc", "find", "diff"}
GAVE_UP = re.compile(r"gave up .*after 300s")


def first_word(command):
    words = re.sub(r"^(cd\s+\S+\s*&&\s*)", "", command.strip()).split()
    while words and re.fullmatch(r"\w+=\S*", words[0]):
        words.pop(0)
    return words[0] if words else ""


def text_of(content):
    if isinstance(content, str):
        return content
    return " ".join(str(b.get("text") or b.get("content") or "") for b in content if isinstance(b, dict))


def replay(files):
    runs, commits, gave_up = set(), {}, 0
    refusals, seen = {"commit": 0, "stop": 0}, set()
    results = []
    for path in files:
        for line in open(path, errors="ignore"):
            d = json.loads(line)
            if d.get("uuid") in seen:
                continue
            seen.add(d.get("uuid"))
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                content = [{"type": "text", "text": content or ""}]
            for b in content:
                if d.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") == "Bash":
                    command = (b.get("input") or {}).get("command", "")
                    if COMMIT.search(command):
                        commits[b["id"]] = True
                    if RUN.search(command) and first_word(command) not in NOT_A_RUN:
                        runs.add(b["id"])
                elif d.get("type") == "user":
                    text = text_of(b.get("content") if b.get("type") == "tool_result" else b.get("text", ""))
                    if GAVE_UP.search(text):
                        gave_up += 1
                    if REFUSED.search(text) and "hook" in text:
                        results.append(b.get("tool_use_id"))
    for tool_use_id in results:
        refusals["commit" if tool_use_id in commits else "stop"] += 1
    return len(runs), refusals, len(commits), gave_up


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--projects", default=os.path.expanduser("~/.claude/projects"))
    args = ap.parse_args()
    print("session | main: runs + refusals (stop, commit) = total | gave up at 300 s | new rule: runs <= commits + refusals <= commit refusals = total")
    main_sum = new_sum = 0
    for name in args.sessions:
        files = sorted(glob.glob(os.path.join(args.projects, f"*-{name}", "*.jsonl")))
        if not files:
            print(f"{name} | cannot tell: no transcript under {args.projects}")
            continue
        runs, ref, commits, gave_up = replay(files)
        main_total, new_total = runs + ref["stop"] + ref["commit"], commits + ref["commit"]
        main_sum, new_sum = main_sum + main_total, new_sum + new_total
        print(f"{name} | {runs} + ({ref['stop']}, {ref['commit']}) = {main_total} | {gave_up} | {commits} + {ref['commit']} = {new_total}")
    print(f"sum | main {main_sum} | new rule {new_sum} | {'below main' if new_sum < main_sum else 'NOT below main'}")


if __name__ == "__main__":
    main()
