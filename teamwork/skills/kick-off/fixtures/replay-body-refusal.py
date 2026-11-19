#!/usr/bin/env python3
"""Check that `use-board.py file` and `edit` refuse a body check-criteria.py refuses, on a git board in a temporary repository, and print `PASS` as the last line when every case holds, else `FAIL`, exit 1:
- `edit`: an edit to a body of 6 criteria exits non-zero naming "more than 5 criteria" and leaves the body sha as it was;
- `file`: a filing of that body exits non-zero and creates no task;
- `held`: an edit of another line of a body that already held 6 criteria is stored.

usage: replay-body-refusal.py [--case <name>]   (no argument: every case)"""
import os
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(LIB))
import criteria_check  # noqa: E402

USE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "use-board.py"
HEAD = "## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n## Definition of done\n\n"
failed = []
ONLY = None


def body(count, goal="The probe has a flow."):
    return HEAD.replace("The probe has a flow.", goal, 1) + "".join(f"{n}. [check] **The probe prints PASS {n}**: `basename PASS` prints `PASS`; on base `FAIL`.\n" for n in range(1, count + 1))


def step(name, ok, detail=""):
    if ONLY and name != ONLY:
        return
    if ok and ONLY:
        return
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[-600:]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args and (len(args) != 2 or args[0] != "--case" or args[1] not in ("edit", "file", "held")):
        print(__doc__, file=sys.stderr)
        return 2
    global ONLY
    ONLY = args[1] if args else None
    work = pathlib.Path(tempfile.mkdtemp(prefix="body-refusal-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    environment = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home"), "PYTHONPATH": str(LIB), "GIT_AUTHOR_NAME": "probe",
                   "GIT_AUTHOR_EMAIL": "probe@example.com", "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@example.com"}

    # the next task takes the cut-off's number, since a task below it keeps the older rules
    floor = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=f"{criteria_check.CUT_OFF - 1}\n", cwd=repository, capture_output=True, text=True, check=True).stdout.strip()
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {floor}\tfloor\n", cwd=repository, capture_output=True, text=True, check=True).stdout.strip()
    commit = subprocess.run(["git", "commit-tree", tree, "-m", "seed"], cwd=repository, env=environment, capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["git", "update-ref", "refs/teamwork-blackboard", commit], cwd=repository, check=True)
    first = criteria_check.CUT_OFF

    def use(*argv):
        return subprocess.run([sys.executable, str(USE), *map(str, argv)], cwd=repository, env=environment, capture_output=True, text=True)

    def write(name, text):
        (work / name).write_text(text)
        return work / name

    def sha(number):
        return next(line.split(": ", 1)[1] for line in use("read", number).stdout.splitlines() if line.startswith("body sha: "))

    def tasks():
        return subprocess.run(["git", "ls-tree", "--name-only", "refs/teamwork-blackboard"], cwd=repository, capture_output=True, text=True).stdout.split()

    filed = use("file", "--title", "Print PASS from the probe", "--body", write("five.md", body(5)))
    before = sha(first)
    done = use("edit", first, "--body", write("six.md", body(6)), "--reason", "adds a sixth criterion.", "--base", before)
    step("edit", filed.returncode == 0 and done.returncode != 0 and "more than 5 criteria" in done.stderr and sha(first) == before, (filed.stderr, done.returncode, done.stderr))

    known = tasks()
    refused = use("file", "--title", "Print PASS six times", "--body", write("six.md", body(6)))
    step("file", refused.returncode != 0 and "more than 5 criteria" in refused.stderr and tasks() == known, (refused.returncode, refused.stderr, tasks()))

    seed = "import board, sys; print(board.file('Probe a held refusal', open(sys.argv[1]).read(), []))"
    held = int(subprocess.run([sys.executable, "-c", seed, str(write("seed.md", body(6)))], cwd=repository, env=environment, capture_output=True, text=True).stdout)
    done = use("edit", held, "--body", write("reworded.md", body(6, "The probe has a flow, reworded.")), "--reason", "rewords the goal.", "--base", sha(held))
    step("held", done.returncode == 0 and "reworded" in use("read", held, "--body").stdout, (done.returncode, done.stderr))
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
