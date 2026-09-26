#!/usr/bin/env python3
"""Start a worker in one call: its name, its worktree, its tab, its Claude session, the folder-trust dialog and its kickoff prompt.

usage: worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <address>] [--owner-effort]

The worker's name and worktree are `lib/names.py`'s, `<k>` the attempt:
1 + the largest `k` of any remote branch, pull request head or local worktree
of task `<n>`, so a reopened task gets a fresh name; `--continue` reuses the
newest local worktree of `<topic>` and `<n>` and resumes its last Claude
session, failing when there is none. The worktree is added detached at
`origin/<default>` when missing; the git guard is copied into the checkout's
hooks, and the worktrees' folder is added to the checkout's `info/exclude`. The
tab sets `MUMU_ROLE=worker`, on which `team-watch` exits at once. Claude runs as
`--agent mumu-team:worker`, started by `lib/herdr.py`'s `launch`. With
`--leader` it is prompted `/mumu-team:kickoff work <task-url> leader <address>`.
`<effort>` must be `low` or `medium`, or it fails with 2 before anything
starts, unless `--owner-effort` says the owner named that effort in so many
words. Prints `<name>@<pane> <worktree>`. `WORKER_START_TIMEOUT` (60) and
`WORKER_START_POLL` (1) are seconds.
"""
import os
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402
from command import run  # noqa: E402
from gh import gh, repo as repo_view  # noqa: E402


def attempts(repo, n):
    """Each `k` of a remote branch, pull request head or local worktree of `repo` named `*-<n>-<k>`."""
    heads = run("git", "-C", repo, "ls-remote", "--heads", "origin").split()
    prs = gh("pr", "list", "--state", "all", "--limit", "1000", "--json", "headRefName", "-q", ".[].headRefName", cwd=repo).split()
    return [k for h in [h.removeprefix("refs/heads/") for h in heads] + prs + local(repo) if (k := names.attempt(h, n=n)) is not None]


def local(repo):
    """The names of `repo`'s local worktrees."""
    trees = names.worktrees(repo)
    return [p.name for p in trees.iterdir()] if trees.is_dir() else []


def worktree(repo, name):
    """The worktree for `name`, added at the default branch unless it exists, with the guard in the checkout's hooks."""
    tree = names.worktrees(repo) / name
    if not tree.exists():
        run("git", "-C", repo, "worktree", "add", "--detach", str(tree), f"origin/{repo_view('defaultBranchRef', repo)}")
    exclude = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").strip())
    text = exclude.read_text() if exclude.exists() else ""
    if names.IGNORE not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text + ("\n" if text and not text.endswith("\n") else "") + names.IGNORE + "\n")
    try:
        run("git", "-C", repo, "config", "core.hooksPath")
    except RuntimeError:
        hooks = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
        guard = shutil.which("default-branch-guard.sh")
        for hook in ("pre-commit", "pre-push"):
            if guard and not (hooks / hook).exists():
                hooks.mkdir(parents=True, exist_ok=True)
                shutil.copy(guard, hooks / hook)
    return tree


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
    if not number or not re.fullmatch(names.TOPIC, topic):
        print(f"worker-start.py: topic {topic!r} must be lowercase words joined by -, and {url!r} a task url", file=sys.stderr)
        return 2
    if effort not in ("low", "medium") and not owner_effort:
        print(f"worker-start.py: effort {effort!r} must be low or medium; pass --owner-effort only when the owner named it", file=sys.stderr)
        return 2
    try:
        repo = str(names.checkout(repo))
        run("git", "-C", repo, "fetch", "origin")
        k = max((k for h in local(repo) if (k := names.attempt(h, topic, number[1])) is not None), default=None) if resume \
            else 1 + max(attempts(repo, number[1]), default=0)
        if k is None:
            raise RuntimeError(f"--continue: no worktree {topic}-{number[1]}-<k> in {names.worktrees(repo)}")
        name = names.worker(topic, number[1], k)
        tree = worktree(repo, name)
        pane = herdr.open_tab(tree, name, "--env", "MUMU_ROLE=worker", "--no-focus")
        timeout, poll = float(os.environ.get("WORKER_START_TIMEOUT", 60)), float(os.environ.get("WORKER_START_POLL", 1))
        herdr.launch(name, pane, ["--name", name, "--agent", "mumu-team:worker", "--model", "opus", "--effort", effort] + (["--continue"] if resume else []), timeout, poll)
        if leader:
            herdr.prompt(pane, f"/mumu-team:kickoff work {url} leader {leader}")
    except RuntimeError as e:
        print(f"worker-start.py: {e}", file=sys.stderr)
        return 1
    print(f"{name}@{pane} {tree}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
