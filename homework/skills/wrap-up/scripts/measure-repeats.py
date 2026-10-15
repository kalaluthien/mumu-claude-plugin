#!/usr/bin/env python3
"""usage: measure-repeats.py [days]

Group failed tool calls of interactive Claude Code sessions by signature and print how many repeat across sessions
and repositories, how fast they spread, and how many are still alive. Read-only over ~/.claude/projects/*/*.jsonl."""
import collections
import glob
import json
import os
import re
import sys
import time

DAYS = float(sys.argv[1]) if len(sys.argv) > 1 else 14
NOW = time.time()
VARIABLE = [(re.compile(p), r) for p, r in [
    (r"/[\w.~@%+-]+(?:/[\w.~@%+-]+)+", "<path>"), (r"\b[0-9a-f]{7,40}\b", "<hash>"),
    (r"https?://\S+", "<url>"), (r"(['\"`]).*?\1", "<q>"), (r"\d+", "<n>"), (r"\s+", " ")]]
NOISE = re.compile(r"^(Exit code <n>|<n>|-+|ok\b.*|This hook comes from .*)$")


def signature(tool, text):
    """The tool and the last meaningful error line, variable parts masked; None for a bare exit code."""
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        for pattern, mask in VARIABLE:
            line = pattern.sub(mask, line)
        if line and not NOISE.match(line):
            lines.append(line)
    reason = re.search(r"\[[A-Z][\w -]+\]", text)
    return f"{tool}: {lines[-1][:100]}" + (f" {reason.group(0)}" if reason else "") if lines else None


def repo(folder):
    return re.sub(r"--claude-worktrees-.*$", "", os.path.basename(folder))


seen = collections.defaultdict(list)  # signature -> [(time, session, repo)]
sessions = 0
for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    if os.path.getmtime(path) < NOW - DAYS * 86400:
        continue
    uses, interactive, found = {}, True, []
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(entry.get("entrypoint", "")).startswith("sdk"):
                interactive = False
            body = (entry.get("message") or {}).get("content")
            for block in body if isinstance(body, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    uses[block.get("id")] = block.get("name")
                elif block.get("type") == "tool_result" and block.get("is_error"):
                    text = block.get("content")
                    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
                    key = signature(uses.get(block.get("tool_use_id"), "?"), text)
                    stamp = entry.get("timestamp", "")
                    if key and stamp:
                        found.append((key, time.mktime(time.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S"))))
    if not interactive:
        continue
    sessions += 1
    for key, stamp in found:
        if stamp >= NOW - DAYS * 86400:
            seen[key].append((stamp, path, repo(os.path.dirname(path))))

spread = {k: v for k, v in seen.items() if len({s for _, s, _ in v}) >= 3}
alive = [k for k, v in spread.items() if max(t for t, _, _ in v) >= NOW - 3 * 86400]
repos = [k for k, v in spread.items() if len({r for _, _, r in v}) >= 2]
days_to_third = sorted(
    (sorted({s: t for t, s, _ in sorted(v, reverse=True)}.values())[2] - min(t for t, _, _ in v)) / 86400
    for v in spread.values())
print(f"window {DAYS:g} days: {sessions} interactive sessions, {sum(map(len, seen.values()))} failures with text, "
      f"{len(seen)} signatures")
print(f"in 3+ sessions: {len(spread)}; of them in 2+ repositories: {len(repos)}; seen in the last 3 days: {len(alive)}")
if days_to_third:
    median = days_to_third[len(days_to_third) // 2]
    within = sum(d <= 7 for d in days_to_third)
    print(f"days from first sighting to third session: median {median:.1f}; within 7 days: {within} of {len(days_to_third)}")
for key, rows in sorted(spread.items(), key=lambda kv: -len({s for _, s, _ in kv[1]}))[:15]:
    print(f"{len({s for _, s, _ in rows}):4} sessions {len(rows):4} failures  {key[:110]}")
