#!/usr/bin/env python3
"""Replay the cleanup of a worker's branch that a pull request merged as a squash, offline: a scratch repository, whose `origin` is a bare repository beside it, holds the worker
`probe-worker`'s worktree and branch, whose commit the squash left off `main`, `GH_REPO` names a GitHub repository and the `gh` stand-in answers `gh pr list` with that merge.
Print `PASS`, else `FAIL: <what differed>` and exit 1.

usage: replay-pull-request-cleanup.py
It checks two things on one scratch repository:
- heartbeat: the manager's heartbeat, `print-team-gaps.py --polls 1`, names the pull request as merged by its worker, which holds nothing open
- cleanup: remove-worktree.py removes the worker's worktree and branch, here and on `origin`, though the squash left the branch commit off `main`, and the heartbeat then names
  no merge of that worker, since the old pull request holds nothing to clean"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

PLUGIN = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "kick-off" / "scripts"
NUMBER, WORKER = 7, "probe-worker"
TEAM = (replay_probe.agent("probe-manager", 1, "working"), replay_probe.agent(WORKER, 2))


def setup(work):
    """A sandbox whose repository and `origin` hold `main` with the worker's change squashed into it and the worker's own branch, which `gh` lists as the merged pull request."""
    sandbox = replay_probe.Sandbox(work, TEAM)
    sandbox.environment["GH_REPO"] = "owner/repository"
    origin = work / "origin.git"
    sandbox.git("init", "-q", "--bare", origin, cwd=work)
    sandbox.git("remote", "add", "origin", origin)
    sandbox.git("push", "-q", "-u", "origin", "main")
    tree = sandbox.repository / ".claude" / "worktrees" / WORKER
    sandbox.git("worktree", "add", "-q", "-b", WORKER, tree, "main")
    replay_probe.write_text(tree, "a.txt", "work\n")
    sandbox.git("add", "a.txt", cwd=tree)
    sandbox.git("commit", "-q", "-m", "work", cwd=tree)
    sandbox.git("push", "-q", "origin", WORKER, cwd=tree)
    sandbox.git("merge", "-q", "--squash", WORKER)
    sandbox.git("commit", "-q", "-m", f"Work (#{NUMBER})")
    sandbox.git("push", "-q", "origin", "main")
    head = sandbox.git("rev-parse", WORKER).strip()
    sandbox.gh([{"number": NUMBER, "headRefName": WORKER, "headRefOid": head, "mergedAt": "2026-01-05T09:00:00Z", "updatedAt": "2026-01-05T09:00:00Z"}])
    return sandbox, tree


def heartbeat(sandbox):
    done = sandbox.python(PLUGIN / "monitors" / "print-team-gaps.py", "--polls", "1", pane="w1:p1", timeout=60, TEAMWORK_MONITOR_POLL=0)
    return done.stdout + done.stderr if done.returncode is not None else f"no exit in 60 s: {done.stdout}{done.stderr}"


def check(work):
    """The first thing that differs from a merged pull request's cleanup, else None."""
    sandbox, tree = setup(work)
    if replay_probe.sh("git", "merge-base", "--is-ancestor", WORKER, "main", cwd=sandbox.repository, environment=sandbox.environment, check=False).returncode == 0:
        return f"{WORKER}'s commit is on main, so the squash merge checks nothing"
    lines = heartbeat(sandbox)
    if f"merged #{NUMBER} by {WORKER}: it holds nothing open" not in lines:
        return f"no merged line for pull request #{NUMBER} of {WORKER}: {lines.strip()}"
    done = sandbox.python(SCRIPTS / "remove-worktree.py", WORKER)
    left = sandbox.git("branch", "--list", WORKER).strip() + sandbox.git("ls-remote", "--heads", "origin", WORKER).strip()
    if left or tree.exists():
        return f"pull request #{NUMBER} is merged but {WORKER} was kept ({left or tree}): {done.stdout.strip()}{done.stderr.strip()}"
    # the branch is gone, so the pull request is history: a worker of that name, as a later one may be, has nothing merged to clean
    again = heartbeat(sandbox)
    if "merged #" in again:
        return f"the cleaned branch {WORKER} is still named merged: {again.strip()}"
    if not any(call.startswith("pr list") for call in sandbox.gh_calls()):
        return f"no `gh pr list` was made, so the merge was never read from the pull requests: {sandbox.gh_calls()}"
    return None


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("pull-request-cleanup-") as work:
        try:
            why = check(work)
        except RuntimeError as e:
            why = str(e)[-400:]
    return replay_probe.fail(why) if why else replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
