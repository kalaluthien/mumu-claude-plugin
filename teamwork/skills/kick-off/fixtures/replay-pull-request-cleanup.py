#!/usr/bin/env python3
"""Replay the cleanup of a branch merged by a real GitHub pull request, read only. A scratch repository, whose `origin` is a bare repository beside it, holds as a local worker
branch the head of the newest merged pull request of `kalaluthien/mumu-claude-plugin` whose branch name has no slash, and `GH_REPO` points `gh pr list` at that repository.
Print `PASS`, else `FAIL: <what differed>` and exit 1. Nothing is written to GitHub: the calls are `gh pr list` and `git fetch`.

usage: replay-pull-request-cleanup.py
It checks two things on one scratch repository:
- heartbeat: the manager's heartbeat line names the pull request as merged by its worker, which holds nothing open
- cleanup: remove-worktree.py removes the worker's worktree and branch, though a squash merge left the branch commits off `main`, and the heartbeat then names no merge of that worker, since the old pull request holds nothing to clean"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
REPO = "kalaluthien/mumu-claude-plugin"
sh = replay_probe.sh


def setup():
    """A scratch repository on `main` with a worktree of the newest merged pull request's head branch; its folder, environment, branch and pull request number."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="pull-request-cleanup-"))
    replay_probe.write_git_config(work)
    environment = {**os.environ, "GIT_CONFIG_GLOBAL": str(work / "gitconfig"), "GH_REPO": REPO}
    repository, origin = work / "repo", work / "origin.git"
    sh("git", "init", "-q", repository, cwd=work, environment=environment)
    (repository / "a.txt").write_text("base\n")
    sh("git", "add", "-A", cwd=repository, environment=environment)
    sh("git", "commit", "-q", "-m", "base", cwd=repository, environment=environment)
    sh("git", "init", "-q", "--bare", origin, cwd=work, environment=environment)
    sh("git", "remote", "add", "origin", origin, cwd=repository, environment=environment)
    sh("git", "push", "-q", "-u", "origin", "main", cwd=repository, environment=environment)
    listing = sh("gh", "pr", "list", "--state", "merged", "--search", "sort:updated-desc", "--limit", "30", "--json", "number,headRefName", "--jq",
                 '[.[] | select(.headRefName | contains("/") | not)][0] | "\\(.number) \\(.headRefName)"',
                 cwd=repository, environment=environment).stdout.split()
    number, branch = listing
    sh("git", "fetch", "-q", "--depth", "1", f"https://github.com/{REPO}.git", f"refs/pull/{number}/head", cwd=repository, environment=environment, timeout=300)
    tree = repository / ".claude" / "worktrees" / branch
    sh("git", "worktree", "add", "-q", "-b", branch, tree, "FETCH_HEAD", cwd=repository, environment=environment)
    return repository, environment, branch, number


def check():
    """The first thing that differs from a merged pull request's cleanup, else None."""
    repository, environment, branch, number = setup()
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import landing, team_gaps; "
            "pulls = landing.pulls('closed', limit=team_gaps.PULL_LIMIT); "
            "listed = [{'name': sys.argv[2], 'pane_id': 'w1:p2', 'agent_status': 'idle'}]; "
            "print('\\n'.join(team_gaps.team_lines([sys.argv[2]], listed, {'prs': pulls, 'everything': []}, {}, {})))")
    lines = sh(sys.executable, "-c", code, LIB, branch, cwd=repository, environment=environment).stdout
    if f"merged #{number} by {branch}: it holds nothing open" not in lines:
        return f"no merged line for pull request #{number} of {branch}: {lines.strip()}"
    done = replay_probe.run_python(SCRIPTS / "remove-worktree.py", repository, environment, branch)
    left = sh("git", "branch", "--list", branch, cwd=repository, environment=environment).stdout.strip()
    if left or (repository / ".claude" / "worktrees" / branch).exists():
        return f"pull request #{number} is merged on GitHub but {branch} was kept: {done.stdout.strip()}{done.stderr.strip()}"
    # the branch is gone, so the pull request is history: a worker of that name, as a later one may be, has nothing merged to clean
    again = sh(sys.executable, "-c", code, LIB, branch, cwd=repository, environment=environment).stdout
    if "merged #" in again:
        return f"the cleaned branch {branch} is still named merged: {again.strip()}"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        why = check()
    except RuntimeError as e:
        why = str(e)[-400:]
    print(f"FAIL: {why}" if why else "PASS")
    return 1 if why else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
