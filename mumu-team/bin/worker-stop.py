#!/usr/bin/env python3
"""Refuse a worker's stop until its issue is closed, a pull request from its branch merged, or its last comment is a record that stops it.

Those records are `BLOCKED:`, `STOPPED:` and `WAITING:`, read in any case with the
colon optional, since GitHub already holds `Blocked` and `Stopped:` comments. Any
later comment, such as the leader's answer to a `BLOCKED:`, sends the worker on.

Stop hook. Only a session run as `--agent mumu-team:worker` is read; any
other stops. The issue is the `<n>` of the worktree `.claude/worktrees/<topic>-<n>`
the session's cwd lies in, and its branch is the worktree's name; a cwd outside
one stops. An issue that `gh` cannot read lets the session stop, so an outage
never traps it.
"""
import json
import re
import subprocess
import sys

RECORD = re.compile(r"\s*(blocked|stopped|waiting)\b", re.I)

payload = json.load(sys.stdin)
if payload.get("agent_type") != "mumu-team:worker":
    sys.exit(0)
tree = re.search(r"/\.claude/worktrees/([^/]+-(\d+))(?:/|$)", payload.get("cwd", ""))
if not tree:
    sys.exit(0)
branch, issue = tree[1], tree[2]


def gh(*args):
    run = subprocess.run(["gh", *args], cwd=payload["cwd"], capture_output=True, text=True)
    try:
        return json.loads(run.stdout)
    except ValueError:
        sys.exit(0)


read = gh("issue", "view", issue, "--json", "state,comments")
if read["state"] == "CLOSED" or read["comments"] and RECORD.match(read["comments"][-1]["body"]):
    sys.exit(0)
prs = gh("pr", "list", "--head", branch, "--state", "merged", "--json", "headRefName,state")
if any(p.get("headRefName") == branch and p.get("state") == "MERGED" for p in prs):
    sys.exit(0)
print(json.dumps({"decision": "block", "reason": (
    f"Issue #{issue} is still open: merge its pull request at an approved sha, or `comment` "
    "`BLOCKED: <question>` on it and `prompt` the leader `see <issue-url>`, or `WAITING: <what>` when another worker "
    "will send you `see <url>`, before you stop.")}))
