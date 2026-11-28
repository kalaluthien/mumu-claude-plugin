#!/usr/bin/env python3
"""Check the git board's edges the board scenario does not reach, in a temporary repository, printing `ok <case>` or `fail <case>: <detail>` per case
then `PASS` or `FAIL`, and exit 1 on any failure; a port read is made by the plugin's lib in a process of the scratch repository's own:
- `changed-since`, `comments-since`, `blockers`, `scoped`, `command`: each port read gives what the writes made, and the comment read finds the one comment written;
- `posted`: `file` and `comment` print a git board's task url and comment url;
- `signal`: a write touches the signal file the task pane watches;
- `outside`: a write outside a repository refuses, naming the repository it needs;
- `stale-lock`: a write blocked by a minute-old `refs/teamwork-blackboard.lock` gives up within 5 seconds, naming that file.

usage: replay-git-board.py"""
import os
import pathlib
import sys
import time

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

USE = LIB.parent / "skills" / "kick-off" / "scripts" / "use-board.py"


def evaluate(sandbox, expression, *modules):
    """EXPRESSION's value, as JSON gives it back, computed with MODULES of the plugin's lib in the sandbox's repository and environment."""
    return sandbox.evaluate(f"import json, {', '.join(modules)}; print(json.dumps({expression}, default=str))")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("git-board-") as work:
        sandbox = replay_probe.Sandbox(work)
        repository, outside = sandbox.repository, work / "outside"
        outside.mkdir()

        def use(*argv, cwd=None):
            return sandbox.python(USE, *map(str, argv), cwd=cwd)

        def port(expression):
            return evaluate(sandbox, expression, "board_git")

        body = replay_probe.write_text(work, "b.md", "A body.\n")
        (repository / "probe").mkdir()
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 5))
        use("file", "--title", "First", "--body", body, "--scope", "probe")
        use("file", "--title", "Second", "--body", body, "--depends", "1")
        use("comment", 1, "--reported", "a comment.")
        reads = {"changed-since": (f"(board_git.changed_since({start!r}), board_git.changed_since('2999-01-01T00:00:00Z'))", lambda got: bool(got[0]) and not got[1]),
                 "comments-since": (f"[(n, note['kind'], note['line']) for n, note in board_git.comments_since({start!r})]", lambda got: got == [[1, "report", "a comment."]]),
                 "blockers": ("board_git.blockers(2)", lambda got: bool(got)),
                 "scoped": ("(board_git.scoped('probe'), board_git.scoped('none'), board_git.fresh(1)['scope'])", lambda got: got[2] == "probe" and got[0] != got[1]),
                 "command": ("board_git.command('use-board.py comment 1 --reported x')", lambda got: got is not None)}
        for name, (read, right) in reads.items():
            got = port(read)
            cases.step(name, right(got), got)

        task_url = use("file", "--title", "Third", "--body", body).stdout.strip()
        comment_url = use("comment", 3, "--reported", "a comment.").stdout.strip()
        cases.step("posted", task_url.startswith("git+file://") and task_url.endswith("/3") and comment_url == f"{task_url}#comment-1", f"{task_url} {comment_url}")

        before = evaluate(sandbox, "team_signal.stamp()", "team_signal")
        time.sleep(0.01)
        wrote = use("label", 3, "--label", "probe")
        cases.step("signal", not wrote.returncode and evaluate(sandbox, "team_signal.stamp()", "team_signal") > before, wrote.stderr)

        refused = use("file", "--title", "Nowhere", "--body", body, cwd=outside)
        cases.step("outside", refused.returncode == 1 and "git repository" in refused.stderr and not refused.stdout, refused.stdout + refused.stderr)

        lock = repository / ".git" / "refs" / "teamwork-blackboard.lock"
        lock.write_text("")
        os.utime(lock, (time.time() - 60,) * 2)  # as a killed writer leaves it
        began = time.time()
        blocked = use("comment", 3, "--reported", "a comment.")
        took = time.time() - began
        lock.unlink()
        cases.step("stale-lock", blocked.returncode == 1 and str(lock) in blocked.stderr and took < 5 and len(port("board_git.fresh(3)['comments']")) == 1,
                   f"{took:.1f} s: {blocked.stdout}{blocked.stderr}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
