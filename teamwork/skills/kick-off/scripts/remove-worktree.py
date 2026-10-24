#!/usr/bin/env python3
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import landing  # noqa: E402


# Only a branch a worker made is deleted on the remote; any other name may be somebody's live branch.
WORKER_BRANCH = re.compile(r"-worker(-[A-Za-z0-9]+)?$")


def git(*argv, cwd):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True)


def unmerged_tips(name, root):
    """Short shas of NAME's local and remote tips that neither `origin/HEAD` nor a merged pull request holds."""
    git("fetch", "origin", cwd=root)
    default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root).stdout.strip()
    tips = {git("rev-parse", "--verify", "--quiet", ref, cwd=root).stdout.strip()
            for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}")} - {""}
    # a squash merge leaves the branch commits off the base, so a merged pull request's head counts as merged too
    merged = {pr["headRefOid"] for pr in landing.pulls("closed", branch=name) or [] if pr["mergedAt"]}
    # with no `origin/HEAD` only a merged pull request counts, so the branch is kept rather than guessed merged
    return sorted(t[:9] for t in tips - merged if not default or git("merge-base", "--is-ancestor", t, default, cwd=root).returncode)


def remove(name, root):
    """What was removed for NAME, or why it stopped: an unclean worktree is kept, never forced."""
    done = []
    tree = root / ".claude" / "worktrees" / name
    git("worktree", "prune", cwd=root)  # a folder deleted by hand leaves its worktree registered
    if tree.exists():
        p = git("worktree", "remove", str(tree), cwd=root)
        if p.returncode:
            return f"{name}: worktree kept, {p.stderr.strip()}"
        done.append("worktree")
    unmerged = unmerged_tips(name, root)
    if unmerged:
        return f"{name}: {', '.join(done) or 'nothing'} removed; branch kept, unmerged commits at {', '.join(unmerged)}"
    if not git("show-ref", "--verify", "--quiet", f"refs/heads/{name}", cwd=root).returncode:
        git("branch", "-D", name, cwd=root)
        done.append("branch")
    if not git("ls-remote", "--exit-code", "origin", f"refs/heads/{name}", cwd=root).returncode:
        if not WORKER_BRANCH.search(name):
            return f"{name}: {', '.join(done) or 'nothing'} removed; origin branch kept, not a worker branch name"
        p = git("push", "origin", "--delete", name, cwd=root)
        if p.returncode:
            return f"{name}: {', '.join(done) or 'nothing'} removed; origin branch kept, {p.stderr.strip()}"
        done.append("origin branch")
    return f"{name}: {', '.join(done) + ' removed' if done else 'nothing left to remove'}"


if not sys.argv[1:]:
    sys.exit("usage: remove-worktree.py <name>...")
common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=".").stdout.strip()
if not common:
    sys.exit("remove-worktree.py: run it inside the checkout.")
root = pathlib.Path(common).parent  # the main checkout, wherever in it this runs
for name in sys.argv[1:]:
    print(remove(name, root))
if not git("remote", "get-url", "origin", cwd=root).returncode:  # with no remote, a local merge already moved the checkout
    p = git("pull", "--ff-only", cwd=root)
    print("checkout fast-forwarded" if not p.returncode else f"checkout not fast-forwarded: {p.stderr.strip()}")
