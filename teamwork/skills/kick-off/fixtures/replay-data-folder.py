#!/usr/bin/env python3
"""Check where the files board and the local changes land with `TEAMWORK_BOARD_DIR` unset, and that their data stays out of commits and out of `.git/teamwork`.
Prints `ok <case>` per passing case and the failing case, then exits 1 when any fails.

usage: replay-data-folder.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = ROOT / "lib"
SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"


def run(argv, cwd, path=None, override=None):
    env = {k: value for k, value in os.environ.items() if k != "TEAMWORK_BOARD_DIR"}
    env.update(**({"TEAMWORK_BOARD_DIR": str(override)} if override else {}), CLAUDE_CONFIG_DIR=str(home), HOME=str(home), PYTHONPATH=str(LIB), TEAMWORK_BOARD="files", TEAMWORK_LANDING="git", **({"PATH": path} if path else {}))
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)


def where(cwd, module, name, path=None, override=None):
    process = run([sys.executable, "-c", f"import {module}; print({module}.{name})"], cwd, path, override)
    return process.stdout.strip() or process.stderr.strip()


def git(repo, *argv):
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True)


def main(args):
    global home
    work = pathlib.Path(tempfile.mkdtemp(prefix="data-folder-")).resolve()
    repo, tree, bare, home = work / "repo", work / "tree", work / "plain", work / "home"
    for new in (repo, bare, home):
        new.mkdir()
    git(repo, "init", "-q")
    git(repo, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "--allow-empty", "-m", "x")
    git(repo, "worktree", "add", "-q", str(tree))
    (repo / ".teamwork").mkdir()
    (repo / ".teamwork" / "settings.json").write_text("{}\n")
    git(repo, "add", ".teamwork/settings.json")  # committed, so an unexcluded data folder shows in status by its own name
    git(repo, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "settings")
    # the data an older version kept in the common folder, which the first read must move
    old = repo / ".git" / "teamwork" / "board" / "7"
    old.mkdir(parents=True)
    (old / "issue.json").write_text('{"title": "old", "labels": [], "state": "OPEN", "reason": "", "parent": null, "blockers": [], "createdAt": "2026-01-01T00:00:00Z", "closedAt": null, "updatedAt": "2026-01-01T00:00:00Z"}')
    (old / "body.md").write_text("old body\n")
    older = repo / ".git" / "teamwork" / "changes"
    older.mkdir()
    (older / "3.json").write_text("{}")
    failed = []

    def step(name, ok, detail=""):
        print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)
        if not ok:
            failed.append(name)

    def matches(got, want):
        return got == want, f"{got} != {want}"

    board, changes = repo / ".teamwork" / "board", repo / ".teamwork" / "changes"
    step("board-folder", *matches([where(folder, "board_files", "FOLDER") for folder in (repo, tree)], [str(board)] * 2))
    step("changes-folder", *matches([where(folder, "landing_git", "folder()") for folder in (repo, tree)], [str(changes)] * 2))
    step("moved", *matches(((board / "7" / "body.md").exists(), (changes / "3.json").exists(), older.exists(), old.parent.exists()), (True, True, False, False)))
    step("override", *matches(where(repo, "board_files", "FOLDER", override=work / "chosen"), str(work / "chosen")))
    text = work / "text.md"
    text.write_text("body\n")
    filed = run([sys.executable, str(SCRIPTS / "use-board.py"), "file", "a title", str(text)], tree)
    step("filed", *matches(filed.returncode, 0))
    changes.mkdir(parents=True, exist_ok=True)
    (changes / "1.json").write_text("{}")  # a change record, as use-landing.py leaves it
    ignored = lambda path: git(repo, "check-ignore", "-q", path).returncode == 0
    step("excluded", *matches((ignored(".teamwork/board/8/issue.json"), ignored(".teamwork/changes/1.json"), ignored(".teamwork/settings.json")), (True, True, False)))
    lines = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    step("exclude-once", *matches((lines.count("/.teamwork/board/"), lines.count("/.teamwork/changes/")), (1, 1)))
    step("clean-status", *matches([line for line in git(repo, "status", "--porcelain").stdout.splitlines() if "board" in line or "changes" in line], []))
    step("no-git-data", *matches((repo / ".git" / "teamwork").exists(), False))
    step("outside", *matches([where(bare, "board_files", "FOLDER"), where(repo, "board_files", "FOLDER", "/nonexistent")], [str(home / "teamwork" / "board")] * 2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
