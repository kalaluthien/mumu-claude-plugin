#!/usr/bin/env python3
"""Stop hook: refuse a worker's or lead's stop while GitHub shows work left, naming its next step.

Only `agent_type` `mumu-team:worker` or `mumu-team:lead` is read; any other
session stops and reads nothing. What `gh` cannot read lets the session stop,
so an outage never traps it.

Worker: the issue is the `<n>` of the worktree `.claude/worktrees/<topic>-<n>`
the cwd lies in, its branch the worktree's name; a cwd outside one stops. It
stops once the issue is closed, a pull request from its branch merged, or the
issue's last comment is `BLOCKED:`, `STOPPED:` or `WAITING:` (any case, the
colon optional). Otherwise the reason names the next step: `merge.py` for an
approved head, fixing a newest `FINDINGS:`, opening a missing pull request.

Lead: its mission is `$CLAUDE_PLUGIN_DATA/mission/<session id>.md`; none, it
stops. It is refused when a monitor of `ensure-monitors.py` is not running, an
open sub-issue of a parent its mission leads has `BLOCKED:` as its last
comment, a `SUBSCRIBE:` line names a worker whose branch merged, or a parent
stays open with every sub-issue closed. Waiting on the owner stops.
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

RECORD = re.compile(r"\s*(blocked|stopped|waiting)\b", re.I)
REVIEW = re.compile(r"\s*(approved|findings)\b", re.I)
BLOCKED = re.compile(r"\s*blocked\b", re.I)
ISSUE = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+)")
SUB_ISSUES = ("query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){"
              "state subIssues(first:100){nodes{url state comments(last:1){nodes{body}}}}}}}")

payload = json.load(sys.stdin)
cwd = payload.get("cwd") or "."


def gh(*args):
    run = subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True)
    try:
        return json.loads(run.stdout)
    except ValueError:
        sys.exit(0)


def tip(repo, branch):
    """The sha the remote `branch` of `repo` (`owner/name`, or `{owner}/{repo}` for cwd's) points at, or None."""
    ref = gh("api", f"repos/{repo}/git/ref/heads/{branch}")
    return ref.get("object", {}).get("sha") if isinstance(ref, dict) else None


def current(prs, repo, branch):
    """Whether a merged one of `prs` is the branch's current claim: its head is the branch's tip, so a merge under a reused name before the reopen does not count."""
    merged = [p["headRefOid"] for p in prs if p["state"] == "MERGED"]
    return bool(merged) and tip(repo, branch) in merged


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def worker():
    tree = re.search(r"/\.claude/worktrees/([^/]+-(\d+))(?:/|$)", cwd)
    if not tree:
        return
    branch, issue = tree[1], tree[2]
    read = gh("issue", "view", issue, "--json", "state,comments")
    if read["state"] == "CLOSED" or read["comments"] and RECORD.match(read["comments"][-1]["body"]):
        return
    prs = [p for p in gh("pr", "list", "--head", branch, "--state", "all", "--json",
                         "url,state,headRefName,headRefOid,comments,reviews") if p.get("headRefName") == branch]
    if current(prs, "{owner}/{repo}", branch):
        return
    pr = next((p for p in prs if p["state"] == "OPEN"), None)
    if pr is None:
        block(f"Issue #{issue} has no open pull request: write the criteria table and open it with `pr`, "
              "then launch its reviewer, before you stop.")
    if approved(pr):
        block(f"{pr['url']} is approved at its head: run `merge.py {pr['url']}` as a Bash call of its own, "
              "then `prompt` the leader `see <pr-url>`; while the owner's sign-off is pending, push any pending commit, "
              "else `comment` `BLOCKED: owner review of <pr-url>` on the issue.")
    notes = [(n.get("createdAt") or n.get("submittedAt") or "", n["body"]) for n in (pr.get("comments") or []) + (pr.get("reviews") or [])]
    records = [body for _, body in sorted(notes) if REVIEW.match(body)]
    if records and records[-1].lstrip()[:8].lower() == "findings":
        block(f"The newest review record on {pr['url']} is `FINDINGS:`: fix each, rerun every criterion, push, "
              f"and resume that reviewer with `SendMessage` `see {pr['url']}`.")
    block(f"Issue #{issue} is still open: merge its pull request at an approved sha, or `comment` "
          "`BLOCKED: <question>` on it and `prompt` the leader `see <issue-url>`, or `WAITING: <what>` when another "
          "worker will send you `see <url>`, before you stop. While your own reviewer or eval runs, wait in one "
          "bounded foreground Bash poll (`for i in $(seq 1 36); do <done-test> && break; sleep 10; done`) instead of stopping.")


def lead():
    path = team.mission_path(os.environ.get("CLAUDE_PLUGIN_DATA", ""), payload.get("session_id"))
    if not path.is_file():
        return
    read = team.read_mission(path.read_text())
    if read is None:
        return
    parents, workers = read
    steps = []
    env = dict(os.environ, CLAUDE_CODE_SESSION_ID=payload.get("session_id", ""))
    missing = subprocess.run([sys.executable, str(BIN / "ensure-monitors.py")], env=env, capture_output=True, text=True)
    if missing.returncode == 0 and missing.stdout.strip():
        steps.append("A lead monitor is not running: run `ensure-monitors.py` and arm each command it prints with the Monitor tool.")
    for parent in parents:
        m = ISSUE.fullmatch(parent)
        if not m:
            continue
        issue = gh("api", "graphql", "-f", f"query={SUB_ISSUES}", "-F", f"o={m[1]}", "-F", f"r={m[2]}", "-F", f"n={m[3]}")
        issue = ((issue.get("data") or {}).get("repository") or {}).get("issue")
        if not issue:
            continue
        subs = issue["subIssues"]["nodes"]
        for sub in subs:
            last = sub["comments"]["nodes"]
            if sub["state"] == "OPEN" and last and BLOCKED.match(last[-1]["body"]):
                steps.append(f"{sub['url']} ends in `BLOCKED:`: `comment` the answer, then `prompt` its worker `see <issue-url>`.")
        if issue["state"] == "OPEN" and subs and all(s["state"] == "CLOSED" for s in subs):
            steps.append(f"Every sub-issue of {parent} is closed: go to Lead 5 and `resolve` it.")
    for name, url in workers.items():
        m = ISSUE.fullmatch(url)
        if m and current(gh("pr", "list", "-R", f"{m[1]}/{m[2]}", "--head", name, "--state", "merged", "--json", "state,headRefOid"),
                         f"{m[1]}/{m[2]}", name):
            steps.append(f"The pull request of {name} merged: `close` its worker with `worker-close.py {name}`.")
    if steps:
        block(" ".join(steps))


if payload.get("agent_type") == "mumu-team:worker":
    worker()
elif payload.get("agent_type") == "mumu-team:lead":
    lead()
