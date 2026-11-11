#!/usr/bin/env python3
"""Check the git board's edges the board scenario does not reach, in a temporary repository, printing `ok <case>` or `fail <case>: <detail>` per case
and exit 1 on any failure:
- `changed-since`, `comments-since`, `blockers`, `scoped`, `trusted`, `command`: each port read gives what the writes made, and the comment read finds the one comment written;
- `posted`: `file` and `comment` print a git board's issue url and comment url;
- `signal`: a write touches the signal file the issue pane watches;
- `outside`: a write outside a repository refuses, naming the repository it needs;
- `stale-lock`: a write blocked by a minute-old `refs/teamwork-blackboard.lock` gives up within 5 seconds, naming that file.

usage: replay-git-board.py"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="git-board-"))
    repository, outside = work / "repo", work / "outside"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    outside.mkdir()
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"))
    os.chdir(repository)
    sys.path.insert(0, str(ROOT / "lib"))
    import board_git
    import team_signal

    def use(*argv, cwd=repository):
        return subprocess.run([sys.executable, str(USE), *map(str, argv)], cwd=cwd, capture_output=True, text=True)

    (work / "b.md").write_text("A body.\n")
    (work / "c.md").write_text("REPORTED: a comment.\n")
    (repository / "probe").mkdir()
    start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 5))
    use("file", "First", work / "b.md", "--scope", "probe")
    use("file", "Second", work / "b.md", "--depends", "1")
    use("comment", 1, work / "c.md")
    reads = {"changed-since": (lambda: (board_git.changed_since(start), board_git.changed_since("2999-01-01T00:00:00Z")), lambda got: bool(got[0]) and not got[1]),
             "comments-since": (lambda: [(n, note["body"]) for n, note in board_git.comments_since(start)], lambda got: got == [(1, "REPORTED: a comment.\n")]),
             "blockers": (lambda: board_git.blockers(2), lambda got: bool(got)),
             "scoped": (lambda: (board_git.scoped("probe"), board_git.scoped("none"), board_git.fresh(1)["scope"]), lambda got: got[2] == "probe" and got[0] != got[1]),
             "trusted": (lambda: board_git.trusted({}), lambda got: got is not None),
             "command": (lambda: board_git.command("use-board.py comment 1 x.md"), lambda got: got is not None)}
    for name, (read, right) in reads.items():
        got = read()
        step(name, right(got), got)

    issue_url = use("file", "Third", work / "b.md").stdout.strip()
    comment_url = use("comment", 3, work / "c.md").stdout.strip()
    step("posted", issue_url.startswith("git+file://") and issue_url.endswith("/3") and comment_url == f"{issue_url}#comment-1", f"{issue_url} {comment_url}")

    before = team_signal.stamp()
    time.sleep(0.01)
    wrote = use("label", 3, "probe")
    step("signal", not wrote.returncode and team_signal.stamp() > before, wrote.stderr)

    refused = use("file", "Nowhere", work / "b.md", cwd=outside)
    step("outside", refused.returncode == 1 and "git repository" in refused.stderr and not refused.stdout, refused.stdout + refused.stderr)

    lock = repository / ".git" / "refs" / "teamwork-blackboard.lock"
    lock.write_text("")
    os.utime(lock, (time.time() - 60,) * 2)  # as a killed writer leaves it
    began = time.time()
    blocked = use("comment", 3, work / "c.md")
    took = time.time() - began
    lock.unlink()
    step("stale-lock", blocked.returncode == 1 and str(lock) in blocked.stderr and took < 5 and len(board_git.fresh(3)["comments"]) == 1, f"{took:.1f} s: {blocked.stdout}{blocked.stderr}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
