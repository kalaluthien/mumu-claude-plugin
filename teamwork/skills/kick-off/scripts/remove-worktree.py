#!/usr/bin/env python3
"""Remove the worktree and every branch each merged worker owns, `<name>` or `<name>-<word>` behind any prefix, local and on
`origin`, then fast-forward the main checkout. An unclean worktree is kept, never forced; a branch with unmerged commits is kept;
a remote branch is deleted only under a worker branch name. A call whose folder is inside a worktree it would remove removes nothing, exits 2 and prints
the call that works from the home folder, since the caller's shell would be left in a deleted folder.

usage: remove-worktree.py <name>... [--repository <folder>]
A name is one word of letters, digits and `-`, else nothing is removed. `--repository` names the checkout, main or worktree, whose repository this removes from."""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import data_folder  # noqa: E402
import landing  # noqa: E402
from landing_git import git  # noqa: E402
import team_names  # noqa: E402


# Only a branch a worker made is deleted on the remote; any other name may be somebody's live branch.
WORKER_BRANCH = re.compile(r"-worker(-[A-Za-z0-9]+)?$")


def merged_heads(branches):
    """The heads of the merged changes: the newest closed ones, and each of BRANCHES by its name too, since the newest alone would forget an old merge of that very branch."""
    found = [landing.pulls("closed"), *(landing.pulls("closed", branch=branch) for branch in branches)]
    return {pull["headRefOid"] for pulls in found for pull in pulls or [] if pull["mergedAt"]}


def unmerged_tips(name, root, heads):
    """Short shas of NAME's local and remote tips that neither `origin/HEAD` nor a merged change's head in HEADS holds."""
    default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root).stdout.strip()
    tips = {git("rev-parse", "--verify", "--quiet", ref, cwd=root).stdout.strip()
            for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}")} - {""}
    # a squash merge leaves the branch commits off the base, so a tip inside the head of a merged change or pull request counts as merged too,
    # which is how a swapped-out worker's branch, the ancestor of its successor's, is retired
    merged = {tip for tip in tips if any(not git("merge-base", "--is-ancestor", tip, head, cwd=root).returncode for head in heads)}
    # with no `origin/HEAD` only a merged pull request counts, so the branch is kept rather than guessed merged
    return sorted(tip[:9] for tip in tips - merged if not default or git("merge-base", "--is-ancestor", tip, default, cwd=root).returncode)


def owned(name, root):
    """The local and `origin` branches NAME owns, by the rule the heartbeat finds its merges with."""
    refs = git("for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads", "refs/remotes/origin", cwd=root).stdout.split()
    return sorted({ref.removeprefix("origin/") for ref in refs if team_names.owns(name, ref.removeprefix("origin/"))} - {"HEAD"})


def drop(branch, root, heads):
    """What was removed of BRANCH, and why any of it was kept, or None."""
    unmerged = unmerged_tips(branch, root, heads)
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


def remove(name, root, branches, heads):
    """What was removed for NAME, its worktree and each of its BRANCHES, and why any was kept: an unclean worktree is kept, never forced."""
    done, kept = [], []
    tree = data_folder.worktree(name)
    git("worktree", "prune", cwd=root)  # a folder deleted by hand leaves its worktree registered
    if tree.exists():
        result = git("worktree", "remove", str(tree), cwd=root)
        if result.returncode:
            return f"{name}: worktree kept, {result.stderr.strip()}"
        done.append("worktree")
    for branch in branches:
        removed, reason = drop(branch, root, heads)
        done += removed
        kept += [reason] if reason else []
    said = ", ".join(done) + " removed" if done else "nothing removed" if kept else "nothing left to remove"
    return f"{name}: {said}" + "".join(f"; {reason}" for reason in kept)


def main(args):
    caller = pathlib.Path.cwd()  # before `--repository` moves this process: the shell that called it stands here
    args = data_folder.enter(args, __doc__)
    if not args or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        for name in args:  # every name is read before any worktree goes
            data_folder.worktree(name)
    except (LookupError, ValueError) as e:
        sys.exit(f"remove-worktree.py: {e}; nothing removed.")
    root = data_folder.main_checkout()  # wherever in it this runs
    inside = [name for name in args if data_folder.worktree(name) in (caller, *caller.parents)]
    if inside:
        script = pathlib.Path(__file__)
        tree = data_folder.worktree(inside[0])
        script = root / script.relative_to(tree) if tree in script.parents else script
        print(f"remove-worktree.py: the folder you stand in is inside the worktree of {', '.join(inside)}, so removing it would leave your shell in a deleted folder; nothing removed. "
                 f'Run: cd ~ && python3 {script} --repository {root} {" ".join(args)}', file=sys.stderr)
        return 2
    os.chdir(root)  # a worker removing its own worktree would otherwise read the landing from a deleted folder and keep its merged branch
    git("fetch", "origin", cwd=root)
    branches = {name: owned(name, root) for name in args}
    heads = merged_heads(sorted({branch for found in branches.values() for branch in found}))
    for name in args:
        print(remove(name, root, branches[name], heads))
    if not git("remote", "get-url", "origin", cwd=root).returncode:  # with no remote, a local merge already moved the checkout
        result = git("pull", "--ff-only", cwd=root)
        print("checkout fast-forwarded" if not result.returncode else f"checkout not fast-forwarded: {result.stderr.strip()}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
