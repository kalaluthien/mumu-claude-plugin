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


def run(argv, cwd, home):
    environment = {**os.environ, "CLAUDE_CONFIG_DIR": str(home), "HOME": str(home), "PYTHONPATH": str(LIB)}
    return subprocess.run(argv, cwd=cwd, env=environment, capture_output=True, text=True)


def where(cwd, home, module, name):
    process = run([sys.executable, "-c", f"import {module}; print({module}.{name})"], cwd, home)
    return process.stdout.strip() or process.stderr.strip()


def git(repository, *argv):
    return subprocess.run(["git", "-C", str(repository), *argv], capture_output=True, text=True)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="data-folder-")).resolve()
    repository, tree, home = work / "repo", work / "tree", work / "home"
    for new in (repository, home):
        new.mkdir()
    git(repository, "init", "-q")
    git(repository, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "--allow-empty", "-m", "x")
    git(repository, "worktree", "add", "-q", str(tree))
    (repository / ".teamwork").mkdir()
    (repository / ".teamwork" / "settings.json").write_text("{}\n")
    git(repository, "add", ".teamwork/settings.json")  # committed, so an unexcluded data folder shows in status by its own name
    git(repository, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "settings")
    # the data an older version kept in the common folder, which the first read must move
    older = repository / ".git" / "teamwork" / "changes"
    older.mkdir(parents=True)
    (older / "3.json").write_text("{}")
    failed = []

    def step(name, ok, detail=""):
        print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
        if not ok:
            failed.append(name)

    def matches(got, want):
        return got == want, f"{got} != {want}"

    changes = repository / ".teamwork" / "changes"
    step("changes-folder", *matches([where(folder, home, "landing_git", "folder()") for folder in (repository, tree)], [str(changes)] * 2))
    step("moved", *matches(((changes / "3.json").exists(), older.exists(), older.parent.exists()), (True, False, False)))
    changes.mkdir(parents=True, exist_ok=True)
    (changes / "1.json").write_text("{}")  # a change record, as use-landing.py leaves it
    ignored = lambda path: git(repository, "check-ignore", "-q", path).returncode == 0
    step("excluded", *matches((ignored(".teamwork/changes/1.json"), ignored(".teamwork/settings.json")), (True, False)))
    lines = (repository / ".git" / "info" / "exclude").read_text().splitlines()
    step("exclude-once", *matches(lines.count("/.teamwork/changes/"), 1))
    step("clean-status", *matches([line for line in git(repository, "status", "--porcelain").stdout.splitlines() if "changes" in line], []))
    step("no-git-data", *matches((repository / ".git" / "teamwork").exists(), False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
