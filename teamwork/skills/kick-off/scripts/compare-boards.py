#!/usr/bin/env python3
"""Compare the git board with the GitHub board for one project: the issue pane's lines, `list-decisions.py` for every open issue and the manager's
heartbeat lines. Prints the first lines that differ, urls aside, then `FAIL`, or `PASS` as its last line when they match; exit 1 on FAIL, so a copy of
the GitHub board into the git board is proved before the switch.

usage: compare-boards.py <project>
       compare-boards.py --print <github|git> <project>
`--print` prints one board's three views, each under a `== <name>` line."""
import contextlib
import difflib
import importlib.util
import io
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
HOOKS = HERE.parents[2] / "hooks"
sys.path.insert(0, str(HERE.parents[2] / "lib"))
# a url differs by board, and a comment's place by what the copy skipped, so each reads as its issue
URL = re.compile(r"(?:https://github\.com/[^/\s)]+/[^/\s)]+/issues|git\+file://\S*?/refs/teamwork/board)/(\d+)(?:#(?:issuecomment|comment)-\d+)?")


def run(script, *argv):
    """What script SCRIPT prints for ARGV, run in this process so the GitHub view's filter applies to it; a refusal or exit reads as a line."""
    spec = importlib.util.spec_from_file_location("shown", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    printed, refused = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(refused):
            status = module.main(list(argv))
    except SystemExit as stop:
        status = stop.code if isinstance(stop.code, int) else 1
        refused.write(stop.code if isinstance(stop.code, str) else "")
    return printed.getvalue() + (f"[exit {status}] {refused.getvalue().strip()}\n" if status else "")


def without_untrusted():
    """The GitHub board as the copy carries it: the copy skips an author the board does not trust, so a stranger's issue is no part of what must match."""
    import board_github
    issues, tree = board_github.issues, board_github.tree
    board_github.issues = lambda *a, **k: (lambda found: found and [record for record in found if record["trusted"]])(issues(*a, **k))
    board_github.tree = lambda project, nodes=None: tree(project, nodes if nodes is not None else (lambda read: read and [n for n in read if board_github.trusted(n)])(board_github.read_tree(project)))


def show(kind, project):
    import board
    import team_gaps
    import landing
    os.environ["TEAMWORK_BOARD"] = kind
    if kind == "github":
        without_untrusted()
    out = ["== pane", run(HOOKS / "list-issue-board.py", project)]
    out.append("== decisions")
    for issue in sorted(board.issues("open", project, comments=False) or [], key=lambda issue: issue["number"]):
        out.append(run(HERE / "list-decisions.py", str(issue["number"])))
    # the heartbeat reads the board only: no landing change and no live session stands in for the team
    landing.pulls = lambda *a, **k: []
    team_gaps.tabs = lambda *a, **k: []
    team_gaps.members = lambda *a, **k: []
    team_gaps.crowding = lambda *a, **k: None
    me = {"name": f"{project}-manager", "workspace_id": ""}
    data = team_gaps.manager_read(me)
    out += ["== heartbeat", "\n".join(sorted(team_gaps.manager_actions(me, [], data, set()) or ["[read failed]"])) + "\n"]
    return "\n".join(out)


def main(args):
    if len(args) == 3 and args[0] == "--print" and args[1] in ("github", "git"):
        sys.stdout.write(show(args[1], args[2]))
        return 0
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    views = {}
    for kind in ("github", "git"):
        done = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()), "--print", kind, args[0]], capture_output=True, text=True)
        if done.returncode:
            print(f"the {kind} board could not be shown: {done.stderr.strip()[-400:]}")
            print("FAIL")
            return 1
        views[kind] = URL.sub(lambda found: f"#{found.group(1)}", done.stdout).splitlines()
    delta = list(difflib.unified_diff(views["github"], views["git"], "github", "git", lineterm="", n=0))
    if delta:
        print("\n".join(delta[:40]))
        print("FAIL")
        return 1
    print(f"the git board and the GitHub board give the same {len(views['git'])} lines")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
