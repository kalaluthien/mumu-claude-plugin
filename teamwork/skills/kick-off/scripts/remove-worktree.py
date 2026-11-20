#!/usr/bin/env python3
"""Remove the worktree and every branch each merged worker owns, `<name>` or `<name>-<word>` behind any prefix, local and on
`origin`, then fast-forward the main checkout. An unclean worktree is kept, never forced; a branch with unmerged commits is kept;
a remote branch is deleted only under a worker branch name.

usage: remove-worktree.py <name>..."""
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import data_folder  # noqa: E402
import landing  # noqa: E402
import team_names  # noqa: E402


# Only a branch a worker made is deleted on the remote; any other name may be somebody's live branch.
WORKER_BRANCH = re.compile(r"-worker(-[A-Za-z0-9]+)?$")


def git(*argv, cwd):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True)


def unmerged_tips(name, root):
    """Short shas of NAME's local and remote tips that neither `origin/HEAD` nor a merged change's head holds."""
    git("fetch", "origin", cwd=root)
    default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root).stdout.strip()
    tips = {git("rev-parse", "--verify", "--quiet", ref, cwd=root).stdout.strip()
            for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}")} - {""}
    # a squash merge leaves the branch commits off the base, so a tip inside the head of a merged change or pull request counts as merged too,
    # which is how a swapped-out worker's branch, the ancestor of its successor's, is retired
    # a name lookup too, since the newest merged pull requests alone would forget an old merge of this very branch
    heads = {pull["headRefOid"] for found in (landing.pulls("closed"), landing.pulls("closed", branch=name)) for pull in found or [] if pull["mergedAt"]}
    merged = {tip for tip in tips if any(not git("merge-base", "--is-ancestor", tip, head, cwd=root).returncode for head in heads)}
    # with no `origin/HEAD` only a merged pull request counts, so the branch is kept rather than guessed merged
    return sorted(tip[:9] for tip in tips - merged if not default or git("merge-base", "--is-ancestor", tip, default, cwd=root).returncode)


def owned(name, root):
    """The local and `origin` branches NAME owns, by the rule the heartbeat finds its merges with."""
    refs = git("for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads", "refs/remotes/origin", cwd=root).stdout.split()
    return sorted({ref.removeprefix("origin/") for ref in refs if team_names.owns(name, ref.removeprefix("origin/"))} - {"HEAD"})


def drop(branch, root):
    """What was removed of BRANCH, and why any of it was kept, or None."""
    unmerged = unmerged_tips(branch, root)
    if unmerged:
        return [], f"branch {branch} kept, unmerged commits at {', '.join(unmerged)}"
    done = []
    if not git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", cwd=root).returncode:
        git("branch", "-D", branch, cwd=root)
        done.append(f"branch {branch}")
    if not git("ls-remote", "--exit-code", "origin", f"refs/heads/{branch}", cwd=root).returncode:
        if not WORKER_BRANCH.search(branch):
            return done, f"origin branch {branch} kept, not a worker branch name"
        result = git("push", "origin", "--delete", branch, cwd=root)
        if result.returncode:
            return done, f"origin branch {branch} kept, {result.stderr.strip()}"
        done.append(f"origin branch {branch}")
    return done, None


def remove(name, root):
    """What was removed for NAME, its worktree and each branch it owns, and why any was kept: an unclean worktree is kept, never forced."""
    done, kept = [], []
    tree = root / ".claude" / "worktrees" / name
    git("worktree", "prune", cwd=root)  # a folder deleted by hand leaves its worktree registered
    if tree.exists():
        result = git("worktree", "remove", str(tree), cwd=root)
        if result.returncode:
            return f"{name}: worktree kept, {result.stderr.strip()}"
        done.append("worktree")
    for branch in owned(name, root):
        removed, reason = drop(branch, root)
        done += removed
        kept += [reason] if reason else []
    said = ", ".join(done) + " removed" if done else "nothing removed" if kept else "nothing left to remove"
    return f"{name}: {said}" + "".join(f"; {reason}" for reason in kept)


def main(args):
    if not args or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    common = data_folder.common_folder()
    if common is None:
        sys.exit("remove-worktree.py: run it inside the checkout.")
    root = common.parent  # the main checkout, wherever in it this runs
    os.chdir(root)  # a worker removing its own worktree would otherwise read the landing from a deleted folder and keep its merged branch
    for name in args:
        print(remove(name, root))
    if not git("remote", "get-url", "origin", cwd=root).returncode:  # with no remote, a local merge already moved the checkout
        result = git("pull", "--ff-only", cwd=root)
        print("checkout fast-forwarded" if not result.returncode else f"checkout not fast-forwarded: {result.stderr.strip()}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
