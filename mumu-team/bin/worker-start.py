#!/usr/bin/env python3
"""Start a worker in one call: its worktree, its tab, its Claude session, the folder-trust dialog, and its first prompt.

usage: worker-start.py <checkout> <name> <effort> [--continue] [--prompt <text>]

The worktree is `<checkout>/.claude/worktrees/<name>`, added detached at
`origin/<default>` when missing and reused when present; the git guard is
copied as `repo.md`'s `checkout` does. Claude runs as `--agent mumu-team:worker`, whose Stop hook
holds it until its issue lands or is blocked. `--continue` resumes the worktree's
last Claude session. The trust dialog defaults to "No, exit", so it is
answered `down enter`. Prints `<name>@<pane> <worktree>` once the session is
ready. `WORKER_START_TIMEOUT` (60) and `WORKER_START_POLL` (1) are seconds.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

TRUST = "Yes, I trust this folder"


def run(*argv, cwd=None):
    """stdout of `argv`, raising with its stderr when it fails."""
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def checkout(repo, name):
    """The worktree for `name`, added at the default branch unless it exists, with the guard in the checkout's hooks."""
    tree = pathlib.Path(repo, ".claude", "worktrees", name)
    if not tree.exists():
        run("git", "-C", repo, "fetch", "origin")
        default = run("gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name", cwd=repo).strip()
        run("git", "-C", repo, "worktree", "add", "--detach", str(tree), f"origin/{default}")
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


def main(argv):
    args, resume, prompt = [], False, None
    it = iter(argv)
    for a in it:
        if a == "--continue":
            resume = True
        elif a == "--prompt":
            prompt = next(it, None)
        else:
            args.append(a)
    if len(args) != 3 or (prompt is None and "--prompt" in argv):
        print("usage: worker-start.py <checkout> <name> <effort> [--continue] [--prompt <text>]", file=sys.stderr)
        return 2
    repo, name, effort = args
    try:
        tree = checkout(repo, name)
        pane = json.loads(run("herdr", "tab", "create", "--cwd", str(tree), "--label", name, "--no-focus"))["result"]["root_pane"]["pane_id"]
        # A trust dialog makes `agent start` report agent_not_ready; await_ready answers it.
        subprocess.run(["herdr", "agent", "start", name, "--kind", "claude", "--pane", pane, "--",
                        "--name", name, "--agent", "mumu-team:worker", "--model", "opus", "--effort", effort] + (["--continue"] if resume else []),
                       capture_output=True, text=True)
        await_ready(name, pane, float(os.environ.get("WORKER_START_TIMEOUT", 60)), float(os.environ.get("WORKER_START_POLL", 1)))
        if prompt:
            run("herdr", "agent", "prompt", pane, prompt)
    except RuntimeError as e:
        print(f"worker-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane} {tree}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
