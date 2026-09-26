#!/usr/bin/env python3
"""Stop hook: refuse a worker's or lead's stop while GitHub shows work left, naming its next step.

Only `agent_type` `mumu-team:worker` or `mumu-team:lead` is read; any other
session stops and reads nothing. What `gh` cannot read lets the session stop,
so an outage never traps it.

Worker: its task is the `<n>` of the worktree `.claude/worktrees/<topic>-<n>-<k>`
the cwd lies in, its branch the worktree's name; a cwd outside one stops. It
stops once the task is closed, or while its last keyword comment is
`BLOCKED:` (any case, the colon optional). Otherwise the reason names the next
step: `merge.py` for an approved head, fixing a newest `FINDINGS:`, opening a
missing pull request.

Lead: refused only while its checkout's repository has an open root goal and
no `team-watch` process descends from `$CLAUDE_PID`; the reason names the
command to arm with the Monitor tool.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

BIN = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BIN.parent / "lib"))
import team  # noqa: E402
from merge import approved  # noqa: E402

KEYWORD = re.compile(r"\s*(blocked|decided|approved|findings)\b", re.I)

payload = json.load(sys.stdin)
cwd = payload.get("cwd") or "."


def gh(*args):
    run = subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True)
    try:
        return json.loads(run.stdout)
    except ValueError:
        sys.exit(0)


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def last_keyword(comments):
    """The lowercased keyword of the newest comment that opens with one, or None."""
    found = [m[1].lower() for c in comments if (m := KEYWORD.match(c["body"]))]
    return found[-1] if found else None


def worker():
    tree = re.search(r"/\.claude/worktrees/([a-z0-9-]+-(\d+)-\d+)(?:/|$)", cwd)
    if not tree:
        return
    branch, task = tree[1], tree[2]
    read = gh("issue", "view", task, "--json", "state,comments")
    if read["state"] == "CLOSED" or last_keyword(read["comments"]) == "blocked":
        return
    prs = [p for p in gh("pr", "list", "--head", branch, "--state", "open", "--json",
                         "url,headRefName,headRefOid,comments,reviews") if p.get("headRefName") == branch]
    if not prs:
        block(f"Task #{task} has no open pull request: write the criteria table and open it with `pr`, "
              "then launch its reviewer, before you stop.")
    pr = prs[0]
    if approved(pr):
        block(f"{pr['url']} is approved at its head: run `merge.py {pr['url']}` as a Bash call of its own, "
              "then `prompt` the leader `see <pr-url>`; while the owner's sign-off is pending, push any pending commit, "
              "else `comment` `BLOCKED: owner review of <pr-url>` on the task.")
    notes = [(n.get("createdAt") or n.get("submittedAt") or "", n["body"]) for n in (pr.get("comments") or []) + (pr.get("reviews") or [])]
    if last_keyword([{"body": body} for _, body in sorted(notes)]) == "findings":
        block(f"The newest review record on {pr['url']} is `FINDINGS:`: fix each, rerun every criterion, push, "
              f"and resume that reviewer with `SendMessage` `see {pr['url']}`.")
    block(f"Task #{task} is still open: merge its pull request at an approved sha, or `comment` "
          "`BLOCKED: <question>` on it and `prompt` the leader `see <task-url>`, before you stop. While your own "
          "reviewer or eval runs, wait in one bounded foreground Bash poll "
          "(`for i in $(seq 1 36); do <done-test> && break; sleep 10; done`) instead of stopping.")


def watching(root):
    """Whether a `team-watch.py` process descends from pid `root`."""
    table = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines()
    rows = [(int(r[0]), int(r[1]), r[2] if len(r) > 2 else "") for r in (line.split(None, 2) for line in table)]
    parent = {pid: ppid for pid, ppid, _ in rows}

    def descends(pid):
        seen = set()
        while pid in parent and pid not in seen:
            seen.add(pid)
            pid = parent[pid]
            if pid == root:
                return True
        return False

    return any("/team-watch.py" in command and descends(pid) for pid, _, command in rows)


def lead():
    goals = team.root_goals(cwd)
    if goals and not watching(int(os.environ.get("CLAUDE_PID") or os.getppid())):
        block(f"You hold open root goals ({' '.join(goals)}) and `team-watch` is not running: arm "
              f"`\"{BIN / 'team-watch.py'}\"` with the Monitor tool at its longest timeout, in your checkout, before you stop.")


if payload.get("agent_type") == "mumu-team:worker":
    worker()
elif payload.get("agent_type") == "mumu-team:lead":
    lead()
