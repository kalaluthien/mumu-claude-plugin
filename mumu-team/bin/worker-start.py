#!/usr/bin/env python3
"""Start a worker in one call: its name, its worktree, its tab, its Claude session, the folder-trust dialog and its kickoff prompt.

usage: worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <address>] [--owner-effort]

The worker's name is `<topic>-<n>-<k>`, `<n>` the task's number and `<k>` its
attempt: 1 + the largest `k` of any remote branch, pull request head or local
worktree named `*-<n>-<k>`, so a reopened task gets a fresh name; `--continue`
reuses the newest local worktree of `<n>` and resumes its last Claude session,
failing when there is none. `<topic>` must be lowercase words joined by `-`.
The worktree is `<checkout>/.claude/worktrees/<name>`, added detached at
`origin/<default>` when missing; the git guard is copied into the checkout's
hooks, and `/.claude/worktrees/` is added to the checkout's `info/exclude` so
worktrees never show as untracked. The tab sets `MUMU_ROLE=worker`, on which
`team-watch` exits at once. Claude runs as `--agent mumu-team:worker`. The trust dialog
defaults to "No, exit", so it is answered `down enter`. Prints
`<name>@<pane> <worktree>`. With `--leader` it is prompted
`/mumu-team:kickoff work <task-url> leader <address>`. `agent start` is
retried while herdr answers `agent_pane_busy`. `<effort>` must be `low` or `medium`, or it fails with 2
before anything starts, unless `--owner-effort` says the owner named that
effort in so many words. `WORKER_START_TIMEOUT` (60) and `WORKER_START_POLL`
(1) are seconds.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

TRUST = "Yes, I trust this folder"
IGNORE = "/.claude/worktrees/"


def run(*argv, cwd=None):
    """stdout of `argv`, raising with its stderr when it fails."""
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def attempts(repo, n):
    """Each `k` of a remote branch, pull request head or local worktree of `repo` named `*-<n>-<k>`."""
    name = re.compile(rf"[a-z0-9]+(?:-[a-z0-9]+)*-{n}-(\d+)")
    heads = run("git", "-C", repo, "ls-remote", "--heads", "origin").split()
    prs = run("gh", "pr", "list", "--state", "all", "--limit", "1000", "--json", "headRefName", "-q", ".[].headRefName", cwd=repo).split()
    trees = pathlib.Path(repo, ".claude", "worktrees")
    local = [p.name for p in trees.iterdir()] if trees.is_dir() else []
    return [int(m[1]) for h in [h.removeprefix("refs/heads/") for h in heads] + prs + local if (m := name.fullmatch(h))]


def local_attempt(repo, topic, n):
    """The newest `k` of a local worktree `<topic>-<n>-<k>` in `repo`, or None."""
    trees = pathlib.Path(repo, ".claude", "worktrees")
    ks = [int(m[1]) for p in (trees.iterdir() if trees.is_dir() else []) if (m := re.fullmatch(rf"{re.escape(topic)}-{n}-(\d+)", p.name))]
    return max(ks, default=None)


def checkout(repo, name):
    """The worktree for `name`, added at the default branch unless it exists, with the guard in the checkout's hooks."""
    tree = pathlib.Path(repo, ".claude", "worktrees", name)
    if not tree.exists():
        default = run("gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name", cwd=repo).strip()
        run("git", "-C", repo, "worktree", "add", "--detach", str(tree), f"origin/{default}")
    exclude = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").strip())
    text = exclude.read_text() if exclude.exists() else ""
    if IGNORE not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text + ("\n" if text and not text.endswith("\n") else "") + IGNORE + "\n")
    if subprocess.run(["git", "-C", repo, "config", "core.hooksPath"], capture_output=True).returncode != 0:
        hooks = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
        guard = shutil.which("default-branch-guard.sh")
        for hook in ("pre-commit", "pre-push"):
            if guard and not (hooks / hook).exists():
                hooks.mkdir(parents=True, exist_ok=True)
                shutil.copy(guard, hooks / hook)
    return tree


def agent(name):
    """herdr's entry for `name`, or None when not listed."""
    for a in json.loads(run("herdr", "agent", "list"))["result"]["agents"]:
        if a.get("name") == name:
            return a
    return None


def await_ready(name, pane, timeout, poll):
    """Answer the trust dialog once it shows, and return when the session is ready for a prompt."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        a = agent(name)
        if a and a.get("interactive_ready") and a.get("agent_status") != "blocked":
            return
        if TRUST in run("herdr", "agent", "read", pane, "--lines", "40"):
            run("herdr", "agent", "send-keys", pane, "down", "enter")
        time.sleep(poll)
    raise RuntimeError(f"{name} not ready after {timeout:g}s; see `herdr agent read {pane}`")


def start(name, pane, claude_args, timeout, poll):
    """`herdr agent start`, retried while the new tab's shell is still busy (`agent_pane_busy`).

    `agent_not_ready` means a trust dialog, which await_ready answers; any other error raises.
    """
    deadline = time.time() + timeout
    while True:
        done = subprocess.run(["herdr", "agent", "start", name, "--kind", "claude", "--pane", pane, "--"] + claude_args,
                              capture_output=True, text=True)
        out = (done.stdout + done.stderr).strip()
        try:
            code = json.loads(out.splitlines()[-1]).get("error", {}).get("code") if out else None
        except (ValueError, AttributeError):
            code = None
        if code is None and done.returncode == 0 or code == "agent_not_ready":
            return
        if code != "agent_pane_busy" or time.time() >= deadline:
            raise RuntimeError(f"herdr agent start {name}: {out}")
        time.sleep(poll)


def main(argv):
    args, resume, leader, owner_effort = [], False, None, False
    it = iter(argv)
    for a in it:
        if a == "--continue":
            resume = True
        elif a == "--owner-effort":
            owner_effort = True
        elif a == "--leader":
            leader = next(it, None)
        else:
            args.append(a)
    if len(args) != 4 or (leader is None and "--leader" in argv):
        print("usage: worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <address>] [--owner-effort]", file=sys.stderr)
        return 2
    repo, topic, effort, url = args
    number = re.search(r"/issues/(\d+)/?$", url)
    if not number or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", topic):
        print(f"worker-start.py: topic {topic!r} must be lowercase words joined by -, and {url!r} a task url", file=sys.stderr)
        return 2
    if effort not in ("low", "medium") and not owner_effort:
        print(f"worker-start.py: effort {effort!r} must be low or medium; pass --owner-effort only when the owner named it", file=sys.stderr)
        return 2
    try:
        run("git", "-C", repo, "fetch", "origin")
        k = local_attempt(repo, topic, number[1]) if resume else 1 + max(attempts(repo, number[1]), default=0)
        if k is None:
            raise RuntimeError(f"--continue: no worktree {topic}-{number[1]}-<k> in {repo}/.claude/worktrees")
        name = f"{topic}-{number[1]}-{k}"
        tree = checkout(repo, name)
        pane = json.loads(run("herdr", "tab", "create", "--cwd", str(tree), "--label", name, "--env", "MUMU_ROLE=worker", "--no-focus"))["result"]["root_pane"]["pane_id"]
        timeout, poll = float(os.environ.get("WORKER_START_TIMEOUT", 60)), float(os.environ.get("WORKER_START_POLL", 1))
        start(name, pane, ["--name", name, "--agent", "mumu-team:worker", "--model", "opus", "--effort", effort] + (["--continue"] if resume else []), timeout, poll)
        await_ready(name, pane, timeout, poll)
        if leader:
            run("herdr", "agent", "prompt", pane, f"/mumu-team:kickoff work {url} leader {leader}")
    except RuntimeError as e:
        print(f"worker-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane} {tree}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
