#!/usr/bin/env python3
"""Check where the files board lands with `TEAMWORK_BOARD_DIR` unset: the git common folder from a repository's root and from its linked worktree, and the
Claude config folder outside a repository or with no git. Prints `ok` and exits 0, else the failing case and exit 1.

usage: replay-board-default-folder.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = ROOT / "lib"


def folder(cwd, path=None):
    env = {k: v for k, v in os.environ.items() if k != "TEAMWORK_BOARD_DIR"}
    env.update(CLAUDE_CONFIG_DIR=str(home), PYTHONPATH=str(LIB), **({"PATH": path} if path else {}))
    run = subprocess.run([sys.executable, "-c", "import board_files; print(board_files.DIR)"], cwd=cwd, env=env, capture_output=True, text=True)
    return run.stdout.strip() or run.stderr.strip()


def main(args):
    global home
    work = pathlib.Path(tempfile.mkdtemp(prefix="board-default-")).resolve()
    repo, tree, bare, home = work / "repo", work / "tree", work / "plain", work / "home"
    for new in (repo, bare, home):  # not `folder`, which would hide the function below
        new.mkdir()
    git = lambda *argv: subprocess.run(["git", "-C", str(repo), *argv], check=True, capture_output=True)
    git("init", "-q")
    git("-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "--allow-empty", "-m", "x")
    git("worktree", "add", "-q", str(tree))
    cases = {"repo root": (repo, None, repo / ".git" / "teamwork" / "board"), "linked worktree": (tree, None, repo / ".git" / "teamwork" / "board"),
             "outside a repository": (bare, None, home / "teamwork" / "board"), "no git on PATH": (repo, "/nonexistent", home / "teamwork" / "board")}
    bad = [f"{name}: {got} != {want}" for name, (cwd, path, want) in cases.items() if (got := folder(cwd, path)) != str(want)]
    print("\n".join(bad) or "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
