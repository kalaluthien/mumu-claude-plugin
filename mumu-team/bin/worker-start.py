#!/usr/bin/env python3
"""Start a worker, or with `--survey` a backlog's survey worker: its name, worktree, tab, Claude session as `--agent mumu-team:worker`, and kickoff prompt."""
import argparse
import os
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402
import github  # noqa: E402
from github import merged, repo as repo_view, run, task  # noqa: E402


def attempts(repo, n, topic=None, remote=True):
    """Each `k` of a local worktree of `repo` for task `n` and `topic`, and with `remote` of each branch and pull request head."""
    trees = names.worktrees(repo)
    found = [p.name for p in trees.iterdir()] if trees.is_dir() else []
    if remote:
        found += [h.removeprefix("refs/heads/") for h in run("git", "-C", repo, "ls-remote", "--heads", "origin").split()]
        found += github.gh("pr", "list", "--state", "all", "--limit", "1000", "--json", "headRefName", "-q", ".[].headRefName", cwd=repo).split()
    return [k for h in found if (k := names.attempt(h, topic, n)) is not None]


def refusal(issue, n, topic, effort, heads, survey=False):
    """Why task `n`, as `task` reads it, may not start a worker on `topic` at `effort`, or with `survey` a survey worker on
    backlog `n`, `heads` the merged pull requests' branches; None when it may."""
    if issue["state"] != "OPEN":
        return f"task #{n} is {issue['state'].lower()}: a stopped or finished task starts no worker; reopen it first"
    if survey:
        return None if "backlog" in issue["labels"] else f"#{n} is not labelled backlog: --survey starts only a backlog's survey worker"
    if "backlog" in issue["labels"]:
        return f"#{n} is labelled backlog, which is never worked: remove the label and write its contract first, or pass --survey to survey it"
    efforts = [label.removeprefix("effort:") for label in issue["labels"] if label.startswith("effort:")]
    if efforts != [effort]:
        return f"task #{n} is labelled {', '.join('effort:' + e for e in efforts) or 'with no effort:<effort>'}: start it at its one effort label"
    if issue["blockers"]:
        return f"task #{n} waits on {', '.join(issue['blockers'])} by blocked-by: start it once each is closed"
    rows = names.shares(issue["body"])
    if rows is not None:
        if topic not in rows:
            return f"task #{n} is split: its topic is a `## Shares` row ({', '.join(rows)}), not {topic!r}"
        waiting = [r for r in rows[topic] if not any(names.attempt(h, r, n) is not None for h in heads)]
        if waiting:
            return f"share {topic!r} of task #{n} is after {', '.join(waiting)}: start it once each has merged"
    return None


def busy(repo, n, topic):
    """The names of `topic`'s attempts on task `n` that have an open pull request or a live tab."""
    heads = github.gh("pr", "list", "--state", "open", "--limit", "1000", "--json", "headRefName", "-q", ".[].headRefName", cwd=repo).split()
    labels = [t.get("label") for t in herdr.listed("tab")]
    return sorted({h for h in heads + labels if names.attempt(h, topic, n) is not None})


def worktree(repo, name):
    """The worktree for `name` on its own new branch `name` from the default branch, unless it exists, with the guard as the checkout's pre-commit hook."""
    tree = names.worktrees(repo) / name
    if not tree.exists():
        run("git", "-C", repo, "worktree", "add", "-b", name, str(tree), f"origin/{repo_view('defaultBranchRef', repo)}")
    exclude = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").strip())
    text = exclude.read_text() if exclude.exists() else ""
    if names.IGNORE not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text + ("\n" if text and not text.endswith("\n") else "") + names.IGNORE + "\n")
    try:
        run("git", "-C", repo, "config", "core.hooksPath")
    except RuntimeError:
        hooks = pathlib.Path(run("git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").strip())
        script = shutil.which("default-branch-guard.sh")
        if script and not (hooks / "pre-commit").exists():
            hooks.mkdir(parents=True, exist_ok=True)
            shutil.copy(script, hooks / "pre-commit")
    return tree


def main(argv):
    parser = argparse.ArgumentParser(prog="worker-start.py", allow_abbrev=False)
    for arg in ("checkout", "topic", "effort", "url"):
        parser.add_argument(arg)
    parser.add_argument("--continue", dest="resume", action="store_true")
    parser.add_argument("--leader")
    parser.add_argument("--owner-effort", action="store_true")
    parser.add_argument("--survey", action="store_true")
    a = parser.parse_args(argv)
    topic, effort, url, resume = a.topic, a.effort, a.url, a.resume
    number = re.search(r"/issues/(\d+)/?$", url)
    if not number or not re.fullmatch(names.TOPIC, topic) or not 2 <= len(topic.split("-")) <= 4:
        print(f"worker-start.py: topic {topic!r} must be 2-4 lowercase words joined by -, and {url!r} a task url", file=sys.stderr)
        return 2
    if effort not in ("low", "medium") and not a.owner_effort:
        print(f"worker-start.py: effort {effort!r} must be low or medium; pass --owner-effort only when the owner named it", file=sys.stderr)
        return 2
    try:
        repo = str(names.checkout(a.checkout))
        issue = task(repo, number[1])
        if why := refusal(issue, number[1], topic, effort, merged(repo) if names.shares(issue["body"]) and not a.survey else [], a.survey):
            raise RuntimeError(why)
        run("git", "-C", repo, "fetch", "origin")
        if not resume and (held := busy(repo, number[1], topic)):
            raise RuntimeError(f"{', '.join(held)} has an open pull request or a live tab: finish or `stop` it before a new attempt, or pass --continue to resume it")
        k = max(attempts(repo, number[1], topic, False), default=None) if resume else 1 + max(attempts(repo, number[1]), default=0)
        if k is None:
            raise RuntimeError(f"--continue: no worktree {topic}-{number[1]}-<k> in {names.worktrees(repo)}")
        name = names.worker(topic, number[1], k)
        tree = worktree(repo, name)
        pane = herdr.open_tab(tree, name, "--env", "MUMU_ROLE=worker", "--no-focus")
        timeout, poll = float(os.environ.get("WORKER_START_TIMEOUT", 60)), float(os.environ.get("WORKER_START_POLL", 1))
        herdr.launch(name, pane, ["--name", name, "--agent", "mumu-team:worker", "--model", "opus", "--effort", effort] + (["--continue"] if resume else []), timeout, poll)
        if a.leader:
            herdr.deliver(name, pane, f"/mumu-team:kickoff {'survey' if a.survey else 'work'} {url} leader {a.leader}", timeout, poll)
    except RuntimeError as e:
        sys.exit(f"worker-start.py: {e}")
    print(f"{name}@{pane} {tree}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
