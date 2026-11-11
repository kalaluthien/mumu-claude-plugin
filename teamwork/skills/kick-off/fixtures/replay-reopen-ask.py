#!/usr/bin/env python3
"""Replay a reopened task whose questions were answered on a board read from another checkout path, and print `PASS` when the heartbeat names
only the question still open, else `FAIL` with what it named. A task holds a question asked and left open, then one a manager answered and one
an owner answered; it is resolved and reopened, and the board is copied to a second repository, where the answers' urls name the first one's git dir.

usage: replay-reopen-ask.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = HERE.parent / "scripts" / "use-board.py"
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="reopen-ask-"))
    os.environ.update({"GIT_CONFIG_GLOBAL": str(work / "gitconfig"), **replay_probe.IDENTITY, "HERDR_PANE_ID": "w1:p1"})
    first, second = work / "first", work / "second"
    for folder in (first, second):
        folder.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=folder, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "start"], cwd=folder, check=True)

    def use(*argv):
        run = subprocess.run([str(USE), *map(str, argv)], cwd=first, capture_output=True, text=True)
        return run.stdout.strip()

    def text(name, body):
        return replay_probe.write_text(work, name, body)

    number = use("file", "Probe a reopened task", text("body.md", "Probe.\n"), "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
    use("hold", number, "w-worker")
    again = use("comment", number, text("ask-again.md", "BLOCKED: which way now?\n"))
    manager_ask = use("comment", number, text("ask-manager.md", "BLOCKED: which way?\n"))
    owner_ask = use("comment", number, text("ask-owner.md", "BLOCKED: merge it?\n"), "--asks", "owner", "--option", "yes", "--option", "no")
    use("decide", number, text("answer-manager.md", "DECIDED: the first way\n"), "--by", "manager", "--answers", manager_ask)
    use("decide", number, text("answer-owner.md", 'DECIDED: merge\n\n> "merge it"\n'), "--by", "owner", "--answers", owner_ask)
    use("resolve", number, text("report.md", "REPORTED: done\n"))
    use("reopen", number)
    subprocess.run(["git", "fetch", "-q", str(first), "refs/teamwork-blackboard:refs/teamwork-blackboard"], cwd=second, check=True)

    os.chdir(second)
    import board
    import team_gaps
    issue = board.fresh(int(number))
    listed = [{"name": "w-worker", "pane_id": "w1:p2", "tab_id": "w1:t2", "workspace_id": "w1", "agent": "claude", "agent_status": "idle"}]
    data = {"found": [issue], "everything": [issue], "prs": [], "outside": [], "feed": [], "links": []}
    named = [line for line in team_gaps.manager_actions({"name": "x-manager", "workspace_id": "w1"}, listed, data, set()) if line.startswith("answer #")]
    ok = len(named) == 1 and again.partition("refs/teamwork-blackboard/")[2] in named[0]
    print("PASS" if ok else "FAIL: " + " | ".join(named))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
