#!/usr/bin/env python3
"""usage: replay-board-default-folder.py

Check where the files board lands with `TEAMWORK_BOARD_DIR` unset: the git common folder from a repository's root and from its linked worktree, and the
Claude config folder outside a repository or with no git. Prints `ok` and exits 0, else the failing case and exit 1."""
import os
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
work = pathlib.Path(tempfile.mkdtemp(prefix="board-default-")).resolve()
repo, tree, bare, home = work / "repo", work / "tree", work / "plain", work / "home"
for folder in (repo, bare, home):
    folder.mkdir()
git = lambda *argv: subprocess.run(["git", "-C", str(repo), *argv], check=True, capture_output=True)
git("init", "-q")
git("-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "--allow-empty", "-m", "x")
git("worktree", "add", "-q", str(tree))


def folder(cwd, path=None):
    env = {k: v for k, v in os.environ.items() if k != "TEAMWORK_BOARD_DIR"}
    env.update(CLAUDE_CONFIG_DIR=str(home), PYTHONPATH=str(LIB), **({"PATH": path} if path else {}))
    run = subprocess.run([sys.executable, "-c", "import board_files; print(board_files.DIR)"], cwd=cwd, env=env, capture_output=True, text=True)
    return run.stdout.strip() or run.stderr.strip()


cases = {"repo root": (repo, None, repo / ".git" / "teamwork" / "board"), "linked worktree": (tree, None, repo / ".git" / "teamwork" / "board"),
         "outside a repository": (bare, None, home / "teamwork" / "board"), "no git on PATH": (repo, "/nonexistent", home / "teamwork" / "board")}
bad = [f"{name}: {got} != {want}" for name, (cwd, path, want) in cases.items() if (got := folder(cwd, path)) != str(want)]
print("\n".join(bad) or "ok")
sys.exit(1 if bad else 0)
