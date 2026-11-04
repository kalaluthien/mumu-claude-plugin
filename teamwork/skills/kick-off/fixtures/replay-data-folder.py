#!/usr/bin/env python3
"""Check where the local changes land, and that their data stays out of commits and out of `.git/teamwork`.
Prints `ok <case>` per passing case and the failing case, then exits 1 when any fails.

usage: replay-data-folder.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = ROOT / "lib"


def run(argv, cwd):
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(home), "HOME": str(home), "PYTHONPATH": str(LIB)}
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)


def where(cwd, module, name):
    process = run([sys.executable, "-c", f"import {module}; print({module}.{name})"], cwd)
    return process.stdout.strip() or process.stderr.strip()


def git(repo, *argv):
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    global home
    work = pathlib.Path(tempfile.mkdtemp(prefix="data-folder-")).resolve()
    repo, tree, home = work / "repo", work / "tree", work / "home"
    for new in (repo, home):
        new.mkdir()
    git(repo, "init", "-q")
    git(repo, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "--allow-empty", "-m", "x")
    git(repo, "worktree", "add", "-q", str(tree))
    (repo / ".teamwork").mkdir()
    (repo / ".teamwork" / "settings.json").write_text("{}\n")
    git(repo, "add", ".teamwork/settings.json")  # committed, so an unexcluded data folder shows in status by its own name
    git(repo, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "settings")
    # the data an older version kept in the common folder, which the first read must move
    older = repo / ".git" / "teamwork" / "changes"
    older.mkdir(parents=True)
    (older / "3.json").write_text("{}")
    failed = []

    def step(name, ok, detail=""):
        print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
        if not ok:
            failed.append(name)

    def matches(got, want):
        return got == want, f"{got} != {want}"

    changes = repo / ".teamwork" / "changes"
    step("changes-folder", *matches([where(folder, "landing_git", "folder()") for folder in (repo, tree)], [str(changes)] * 2))
    step("moved", *matches(((changes / "3.json").exists(), older.exists(), older.parent.exists()), (True, False, False)))
    changes.mkdir(parents=True, exist_ok=True)
    (changes / "1.json").write_text("{}")  # a change record, as use-landing.py leaves it
    ignored = lambda path: git(repo, "check-ignore", "-q", path).returncode == 0
    step("excluded", *matches((ignored(".teamwork/changes/1.json"), ignored(".teamwork/settings.json")), (True, False)))
    lines = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    step("exclude-once", *matches(lines.count("/.teamwork/changes/"), 1))
    step("clean-status", *matches([line for line in git(repo, "status", "--porcelain").stdout.splitlines() if "changes" in line], []))
    step("no-git-data", *matches((repo / ".git" / "teamwork").exists(), False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
