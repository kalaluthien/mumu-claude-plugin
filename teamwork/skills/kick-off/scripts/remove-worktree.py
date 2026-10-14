#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


def git(*argv, cwd):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True)


def unmerged_tips(name, root):
    """Short shas of NAME's local and remote tips that neither the default branch nor a merged pull request holds."""
    git("fetch", "origin", cwd=root)
    default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root).stdout.strip() or "origin/main"
    tips = {git("rev-parse", "--verify", "--quiet", ref, cwd=root).stdout.strip()
            for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}")} - {""}
    # a squash merge leaves the branch commits off the default branch, so a merged pull request's head counts as merged too
    prs = subprocess.run(["gh", "pr", "list", "--head", name, "--state", "merged", "--json", "headRefOid"],
                         cwd=root, capture_output=True, text=True)
    merged = {pr["headRefOid"] for pr in json.loads(prs.stdout or "[]")}
    return sorted(t[:9] for t in tips - merged if git("merge-base", "--is-ancestor", t, default, cwd=root).returncode)


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
p = git("pull", "--ff-only", cwd=root)
print("checkout fast-forwarded" if not p.returncode else f"checkout not fast-forwarded: {p.stderr.strip()}")
