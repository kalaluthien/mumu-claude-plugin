#!/usr/bin/env python3
"""Check that the board refuses a task Goal that names no flow of its changed part when it is filed or edited, on a git board in a temporary repository, and print `PASS` as the last line when the case holds, else `FAIL: <what differed>` and exit 1.

usage: replay-goal-write.py --case <name>
- task: `file` and `edit` each refuse a Goal with no `Path:` line, naming check-criteria.py's own fix and writing nothing, and write a Goal that names its path
- shared: the fix a refused write prints is the one check-criteria.py prints for the same Goal, and no script holds a second copy of the rule
- other: a part-list edit of a body whose Goal already lacked a path, a body with no Goal, a task below the Goal cut-off and a decision are not refused"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parents[1]
LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import criteria_check  # noqa: E402
import replay_probe  # noqa: E402

BOARD = SKILL / "scripts" / "use-board.py"
CHECKER = SKILL / "scripts" / "check-criteria.py"
CRITERION = "1. [check] **The probe prints PASS when it runs**: `echo ok` prints `ok`; on base nothing.\n"
PATHLESS = "## Goal\n\nChange the heartbeat hook so it lists each worker's open task.\n\n## Definition of done\n\n" + CRITERION
WITH_PATH = PATHLESS.replace("task.\n", "task.\n\nPath: caller: the session start; after: the board write; meets: the owner in the pane\n", 1)
NO_GOAL = "Root intent of the owner.\n\n## Definition of done\n\n" + CRITERION


def start(floor):
    """(work folder, repository, environment) of a repository whose next issue takes the number FLOOR + 1."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="goal-write-"))
    repository = work / "proj"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    environment = {**os.environ, **replay_probe.IDENTITY, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    floor = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=f"{floor}\n", cwd=repository, capture_output=True, text=True, check=True).stdout.strip()
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {floor}\tfloor\n", cwd=repository, capture_output=True, text=True, check=True).stdout.strip()
    commit = subprocess.run(["git", "commit-tree", tree, "-m", "seed"], cwd=repository, env=environment, capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["git", "update-ref", "refs/teamwork-blackboard", commit], cwd=repository, check=True)
    return work, repository, environment


def board(repository, environment, *argv):
    return replay_probe.run_python(BOARD, repository, environment, *argv)


def body_sha(repository, environment, number):
    shown = board(repository, environment, "read", number).stdout
    return next(line.split("body sha: ")[1].strip() for line in shown.splitlines() if "body sha: " in line)


def edit(work, repository, environment, number, old, new, line="DECIDED: change the body"):
    (work / "old").write_text(old)
    (work / "new").write_text(new)
    diff = subprocess.run(["diff", "-u", "--label", "a/body", "--label", "b/body", "old", "new"], cwd=work, capture_output=True, text=True).stdout
    (work / "edit.diff").write_text(diff)
    return board(repository, environment, "edit", number, work / "edit.diff", line, "--base", body_sha(repository, environment, number))


def file_body(work, repository, environment, name, text):
    (work / name).write_text(text)
    return board(repository, environment, "file", "Probe the Goal", work / name)


def case_task():
    work, repository, environment = start(criteria_check.GOAL_CUT_OFF - 1)
    refused = file_body(work, repository, environment, "pathless.md", PATHLESS)
    if refused.returncode != 2 or "no path in the Goal" not in refused.stderr or board(repository, environment, "read", criteria_check.GOAL_CUT_OFF).returncode == 0:
        return replay_probe.fail(f"a pathless Goal was filed or not named: exit {refused.returncode}, {refused.stderr.strip()[-200:]!r}")
    filed = file_body(work, repository, environment, "path.md", WITH_PATH)
    if filed.returncode or not filed.stdout.strip().endswith(f"/{criteria_check.GOAL_CUT_OFF}"):
        return replay_probe.fail(f"a Goal with a path was not filed as #{criteria_check.GOAL_CUT_OFF}: exit {filed.returncode}, {filed.stderr.strip()[-200:]!r}")
    before = board(repository, environment, "read", criteria_check.GOAL_CUT_OFF).stdout
    edited = edit(work, repository, environment, criteria_check.GOAL_CUT_OFF, WITH_PATH, PATHLESS)
    if edited.returncode != 2 or "no path in the Goal" not in edited.stderr or board(repository, environment, "read", criteria_check.GOAL_CUT_OFF).stdout != before:
        return replay_probe.fail(f"an edit that drops the path was not refused cleanly: exit {edited.returncode}, {edited.stderr.strip()[-200:]!r}")
    kept = edit(work, repository, environment, criteria_check.GOAL_CUT_OFF, WITH_PATH, WITH_PATH.replace("open task", "open task and its parts"))
    if kept.returncode:
        return replay_probe.fail(f"an edit that keeps the path was refused: {kept.stderr.strip()[-200:]!r}")
    return 0


def case_shared():
    work, repository, environment = start(criteria_check.GOAL_CUT_OFF - 1)
    refused = file_body(work, repository, environment, "pathless.md", PATHLESS)
    (work / "lint.md").write_text(PATHLESS)
    linted = subprocess.run([sys.executable, str(CHECKER), str(work / "lint.md")], capture_output=True, text=True).stdout
    fix = re.search(r"^- no path in the Goal: (.*)$", linted, re.M)
    if not fix or fix.group(1) not in refused.stderr:
        return replay_probe.fail(f"the refusal does not carry check-criteria.py's fix {fix and fix.group(1)!r}: {refused.stderr.strip()[-300:]!r}")
    copies = [path.name for path in (SKILL / "scripts").glob("*.py") if "PATH_LINE" in path.read_text() or "NOBODY" in path.read_text()]
    if copies:
        return replay_probe.fail(f"{copies} hold a second copy of the Goal rule outside lib/criteria_check.py")
    return 0


def seed(repository, environment, text):
    """The number of an issue written straight to the board, as a Goal filed before this check was, which `file` would refuse."""
    code = "import board, sys; print(board.file('Probe a held Goal', open(sys.argv[1]).read(), []))"
    done = subprocess.run([sys.executable, "-c", code, str(repository.parent / "seed.md")], cwd=repository, env={**environment, "PYTHONPATH": str(LIB)}, capture_output=True, text=True)
    return int(done.stdout)


def case_other():
    work, repository, environment = start(criteria_check.GOAL_CUT_OFF - 1)
    (work / "seed.md").write_text(PATHLESS)
    held = seed(repository, environment, PATHLESS)
    more = edit(work, repository, environment, held, PATHLESS, PATHLESS + "2. [check] **The probe prints PASS twice**: `echo ok` prints `ok`; on base nothing.\n")
    if more.returncode:
        return replay_probe.fail(f"an edit of another part of a body whose Goal already lacked a path was refused: {more.stderr.strip()[-200:]!r}")
    root = file_body(work, repository, environment, "root.md", NO_GOAL)
    if root.returncode:
        return replay_probe.fail(f"a body with no Goal was refused: {root.stderr.strip()[-200:]!r}")
    (work / "decision.md").write_text("DECIDED: the probe holds this.\n\n```teamwork\nholders: probe-worker\n```\n")
    decided = board(repository, environment, "decide", held, work / "decision.md")
    if decided.returncode:
        return replay_probe.fail(f"a decision on a task with a pathless Goal was refused: {decided.stderr.strip()[-200:]!r}")
    work, repository, environment = start(0)
    (work / "seed.md").write_text(WITH_PATH)
    old = seed(repository, environment, WITH_PATH)
    reworded = edit(work, repository, environment, old, WITH_PATH, PATHLESS)
    if old >= criteria_check.GOAL_CUT_OFF or reworded.returncode:
        return replay_probe.fail(f"an edit of task #{old}, below the Goal cut-off, to a Goal with no path was refused: {reworded.stderr.strip()[-200:]!r}")
    return 0


CASES = {"task": case_task, "shared": case_shared, "other": case_other}


def main(args):
    if len(args) != 2 or args[0] != "--case" or args[1] not in CASES:
        print(__doc__, file=sys.stderr)
        return 2
    if CASES[args[1]]():
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
