#!/usr/bin/env python3
"""Check the git board's edges the board scenario does not reach, in a temporary repository, printing `ok <case>` or `fail <case>: <detail>` per case
and exit 1 on any failure:
- `changed-since`, `comments-since`, `blockers`, `scoped`, `trusted`, `command`: each port read gives on the git board what it gives on the files
  board for the same writes, and the comment read finds the one comment written;
- `posted`: `posted()` reads back the body behind a git board's issue url and comment url;
- `signal`: a write touches the signal file the issue pane watches;
- `outside`: a write outside a repository refuses, naming the repository it needs;
- `stale-lock`: a write blocked by a minute-old `refs/teamwork/board.lock` gives up within 5 seconds, naming that file;
- `copy-refused`: copy-board.py refuses a target holding an issue, leaving it unchanged.

usage: replay-git-board.py"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
COPY = ROOT / "skills" / "kick-off" / "scripts" / "copy-board.py"
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    failed.extend([] if ok else [name])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="git-board-"))
    repo, outside = work / "repo", work / "outside"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    outside.mkdir()
    os.environ.update(TEAMWORK_BOARD_DIR=str(work / "board"), HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"))
    os.chdir(repo)
    sys.path.insert(0, str(ROOT / "lib"))
    import board_files
    import board_git
    import team_settings
    import team_signal

    def use(kind, *argv, cwd=repo):
        return subprocess.run([sys.executable, str(USE), *map(str, argv)], env={**os.environ, "TEAMWORK_BOARD": kind}, cwd=cwd, capture_output=True, text=True)

    (work / "b.md").write_text("A body.\n")
    (work / "c.md").write_text("A comment.\n")
    scope = team_settings.load(os.getcwd())["scope_prefix"] + "probe"
    start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 5))
    for kind in ("files", "git"):
        use(kind, "file", "First", work / "b.md", scope)
        use(kind, "file", "Second", work / "b.md")
        use(kind, "order", 2, 1)
        use(kind, "comment", 1, work / "c.md")
    reads = {"changed-since": lambda module: (module.changed_since(start), module.changed_since("2999-01-01T00:00:00Z")),
             "comments-since": lambda module: [(n, note["body"]) for n, note in module.comments_since(start)],
             "blockers": lambda module: module.blockers(2), "scoped": lambda module: (module.scoped("probe"), module.scoped("none")),
             "trusted": lambda module: module.trusted({}), "command": lambda module: module.command("use-board.py comment 1 x.md")}
    for name, read in reads.items():
        files, git = read(board_files), read(board_git)
        step(name, files == git and (name != "comments-since" or git == [(1, "A comment.\n")]), f"files {files}, git {git}")

    issue_url = use("git", "file", "Third", work / "b.md").stdout.strip()
    comment_url = use("git", "comment", 3, work / "c.md").stdout.strip()
    step("posted", board_git.posted(f"posted {issue_url}\n") == (issue_url, "A body.\n") and board_git.posted(comment_url) == (comment_url, "A comment.\n")
         and issue_url.startswith("git+file://"), f"{issue_url} {comment_url}: {board_git.posted(issue_url)} {board_git.posted(comment_url)}")

    before = team_signal.stamp()
    time.sleep(0.01)
    wrote = use("git", "label", 3, "probe")
    step("signal", not wrote.returncode and team_signal.stamp() > before, wrote.stderr)

    refused = use("git", "file", "Nowhere", work / "b.md", cwd=outside)
    step("outside", refused.returncode == 1 and "git repository" in refused.stderr and not refused.stdout, refused.stdout + refused.stderr)

    lock = repo / ".git" / "refs" / "teamwork" / "board.lock"
    lock.write_text("")
    os.utime(lock, (time.time() - 60,) * 2)  # as a killed writer leaves it
    began = time.time()
    blocked = use("git", "comment", 3, work / "c.md")
    took = time.time() - began
    lock.unlink()
    step("stale-lock", blocked.returncode == 1 and str(lock) in blocked.stderr and took < 5 and len(board_git.fresh(3)["comments"]) == 1, f"{took:.1f} s: {blocked.stdout}{blocked.stderr}")

    tip = subprocess.run(["git", "rev-parse", board_git.REF], capture_output=True, text=True).stdout
    copied = subprocess.run([sys.executable, str(COPY), "files", "git"], capture_output=True, text=True)
    after = subprocess.run(["git", "rev-parse", board_git.REF], capture_output=True, text=True).stdout
    step("copy-refused", copied.returncode == 1 and "#1, #2, #3" in copied.stderr and tip == after, copied.stdout + copied.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
