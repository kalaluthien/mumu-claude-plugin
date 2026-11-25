#!/usr/bin/env python3
"""Check that `use-board.py file` and `edit` refuse a body check-criteria.py refuses, on a scratch git board whose tasks take numbers past both rule
cut-offs, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `file <row>`, `edit <row>`: for each row of BAD, a filing of the bad body, and an edit of a filed task to it, exits 2 naming the row's message
  and leaves the board ref where it was;
- `shown`: the pane's list shows the filed task's criterion sentence on its `☐` line;
- `shared`: the Goal fix a refused filing prints is the one check-criteria.py prints for the same body, and no script holds a second copy of the rule;
- `held <row>`: an edit of another line of a body written straight to the board with the row's defect, as a body filed before the rule was, is stored;
- `other`: a body with no Goal is filed, a decision on a task whose Goal lacks a path is stored, and a task below the Goal cut-off is edited to a Goal with no path.

usage: replay-body-gate.py"""
import pathlib
import re
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
LIB = SKILL.parents[1] / "lib"
sys.path.insert(0, str(LIB))
import criteria_check  # noqa: E402
import replay_probe  # noqa: E402

USE = SKILL / "scripts" / "use-board.py"
CHECKER = SKILL / "scripts" / "check-criteria.py"
LISTER = SKILL.parents[1] / "hooks" / "list-task-board.py"
GOOD = replay_probe.BODY
NAME = "The probe prints PASS when it runs"
PATHLESS = GOOD.replace("Path: caller: the probe run; meets: the owner\n\n", "")
# each row: its name, a body check-criteria.py refuses, the words its refusal holds
BAD = (("criteria", GOOD + "".join(f"{n}. [check] **The probe prints PASS {n}**: `basename PASS` prints `PASS`; on base `FAIL`.\n" for n in range(2, 7)), "more than 5 criteria"),
       ("label", GOOD.replace(NAME, "Four closed"), "Complete sentence"),
       ("goal", PATHLESS, "no path in the Goal"))


def floor(box, below, cwd=None):
    """The board of CWD made to give its next task the number BELOW + 1."""
    blob = box.run(["git", "hash-object", "-w", "--stdin"], cwd=cwd, input=f"{below}\n").stdout.strip()
    tree = box.run(["git", "mktree"], cwd=cwd, input=f"100644 blob {blob}\tfloor\n").stdout.strip()
    box.git("update-ref", "refs/teamwork-blackboard", box.git("commit-tree", tree, "-m", "seed", cwd=cwd).strip(), cwd=cwd)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("body-gate-") as work:
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 1)]))


def replay(box):
    cases = replay_probe.Cases()
    step = cases.step

    def use(*argv, cwd=None):
        return box.python(USE, *map(str, argv), cwd=cwd)

    def body(name, text):
        return replay_probe.write_text(box.work, f"{name}.md", text)

    def ref(cwd=None):
        return box.git("rev-parse", "refs/teamwork-blackboard", cwd=cwd).strip()

    def sha(number, cwd=None):
        return re.search(r"body sha: (\w+)", use("read", number, cwd=cwd).stdout).group(1)

    def number(url):
        return int(url.strip().rsplit("/", 1)[-1])

    def seed(name, text, cwd=None):
        """The number of a task written straight to the board, as a body filed before its rule was, which `file` would refuse."""
        code = "import board, sys; print(board.file('Probe a held body', open(sys.argv[1]).read(), []))"
        return box.evaluate(code, body(name, text), cwd=cwd)

    floor(box, max(criteria_check.CUT_OFF, criteria_check.GOAL_CUT_OFF) - 1)
    filed = use("file", "--title", "Probe the gate", "--body", body("good", GOOD))
    task = number(filed.stdout) if filed.returncode == 0 else None
    refusals = {}
    for row, bad, message in BAD:
        for verb in ("file", "edit"):
            before = ref()
            refusals[row, verb] = done = (use("file", "--title", "Probe the gate again", "--body", body(row, bad)) if verb == "file" else
                                          use("edit", task, "--body", body(row, bad), "--reason", f"adds a {row} defect", "--base", sha(task)))
            step(f"{verb} {row}", task and done.returncode == 2 and message in done.stderr and ref() == before,
                 f"filed: {filed.stderr}; exit {done.returncode}, board moved {ref() != before}, {done.stderr}")

    shown = box.python(LISTER, "").stdout
    step("shown", f"☐ {NAME}" in shown and "○ " not in shown, shown)

    linted = box.python(CHECKER, body("lint", PATHLESS)).stdout
    fix = re.search(r"^- no path in the Goal: (.*)$", linted, re.M)
    copies = [path.name for path in (SKILL / "scripts").glob("*.py") if "PATH_LINE" in path.read_text() or "NOBODY" in path.read_text()]
    step("shared", fix and fix.group(1) in refusals["goal", "file"].stderr and not copies,
         f"check-criteria.py's fix {fix and fix.group(1)!r}, the refusal {refusals['goal', 'file'].stderr!r}, second copies in {copies}")

    for row, bad, _ in BAD:
        held = seed(f"held-{row}", bad)
        done = use("edit", held, "--body", body(f"reworded-{row}", bad.replace("A summary.", "A summary, reworded.")), "--reason", "rewords the summary", "--base", sha(held))
        step(f"held {row}", done.returncode == 0 and "reworded" in use("read", held, "--body").stdout, (done.returncode, done.stderr))

    no_goal = use("file", "--title", "Probe a root", "--body", body("root", "Root intent of the owner.\n\n## Definition of done\n\n" + replay_probe.CHECK))
    decided = use("decide", seed("decided", PATHLESS), "--decision", "the probe holds this.", "--by", "probe-manager", "--holders", "probe-worker")
    old = box.init(box.work / "old")
    floor(box, 0, cwd=old)
    below = seed("old", GOOD, cwd=old)
    reworded = use("edit", below, "--body", body("old-pathless", PATHLESS), "--reason", "drops the path", "--base", sha(below, old), cwd=old)
    step("other", no_goal.returncode == 0 and decided.returncode == 0 and below < criteria_check.GOAL_CUT_OFF and reworded.returncode == 0,
         [(done.returncode, done.stderr) for done in (no_goal, decided, reworded)])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
