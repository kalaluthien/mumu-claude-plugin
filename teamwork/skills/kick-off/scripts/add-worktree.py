#!/usr/bin/env python3
"""Add a worker's worktree at `.claude/worktrees/<name>` of the main checkout, wherever in the checkout this runs, so it
sits beside the other workers' and remove-worktree.py finds it; print its path.

usage: add-worktree.py <name> <base> [<branch>] [--repository <folder>]
BRANCH, by default NAME, is made from BASE (`main` with no remote, `origin/main` with one). `--repository` names the checkout, main or worktree, whose repository this adds to."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import data_folder  # noqa: E402
import landing_git  # noqa: E402


def main(args):
    args = data_folder.enter(args, __doc__)
    if len(args) not in (2, 3) or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    name, base, branch = args[0], args[1], args[2] if args[2:] else args[0]
    try:
        tree = data_folder.worktree(name)
    except (LookupError, ValueError) as e:
        sys.exit(f"add-worktree.py: {e}")
    result = landing_git.git("worktree", "add", "-b", branch, str(tree), base, cwd=data_folder.main_checkout())
    if result.returncode:
        sys.exit(f"add-worktree.py: {result.stderr.strip()}")
    print(tree)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
