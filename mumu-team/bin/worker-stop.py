#!/usr/bin/env python3
"""Refuse a worker's stop until its issue is closed, as its merged pull request closes it, or holds a `BLOCKED:` comment.

Stop hook. Only a session run as `--agent mumu-team:worker` is read; any
other stops. The issue is the `<n>` of the worktree `.claude/worktrees/<topic>-<n>`
the session's cwd lies in; a cwd outside one stops. An issue that `gh` cannot
read lets the session stop, so an outage never traps it.
"""
import json
import re
import subprocess
import sys

payload = json.load(sys.stdin)
if payload.get("agent_type") != "mumu-team:worker":
    sys.exit(0)
tree = re.search(r"/\.claude/worktrees/[^/]+-(\d+)(?:/|$)", payload.get("cwd", ""))
if not tree:
    sys.exit(0)
issue = tree[1]
view = subprocess.run(["gh", "issue", "view", issue, "--json", "state,comments"],
                      cwd=payload["cwd"], capture_output=True, text=True)
try:
    read = json.loads(view.stdout)
except ValueError:
    sys.exit(0)
if read["state"] == "CLOSED" or any(c["body"].lstrip().startswith("BLOCKED:") for c in read["comments"]):
    sys.exit(0)
print(json.dumps({"decision": "block", "reason": (
    f"Issue #{issue} is still open: merge its pull request at an approved sha, or `comment` "
    "`BLOCKED: <question>` on it and `prompt` the leader `see <issue-url>`, before you stop.")}))
