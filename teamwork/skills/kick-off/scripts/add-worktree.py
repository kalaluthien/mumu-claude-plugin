#!/usr/bin/env python3
"""Add a worker's worktree at `.claude/worktrees/<name>` of the main checkout, wherever in the checkout this runs, so it
sits beside the other workers' and remove-worktree.py finds it; print its path.

usage: add-worktree.py <name> <base> [<branch>]
BRANCH, by default NAME, is made from BASE (`main` with no remote, `origin/main` with one)."""
import pathlib
import subprocess
import sys


def git(*argv, cwd):
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True)


def main(args):
    if len(args) not in (2, 3) or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    name, base, branch = args[0], args[1], args[2] if args[2:] else args[0]
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=".").stdout.strip()
    if not common:
        sys.exit("add-worktree.py: run it inside the checkout.")
    root = pathlib.Path(common).parent  # the main checkout, as remove-worktree.py finds it
    tree = root / ".claude" / "worktrees" / name
    result = git("worktree", "add", "-b", branch, str(tree), base, cwd=root)
    if result.returncode:
        sys.exit(f"add-worktree.py: {result.stderr.strip()}")
    print(tree)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
