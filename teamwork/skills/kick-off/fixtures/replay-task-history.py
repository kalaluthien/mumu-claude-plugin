#!/usr/bin/env python3
"""Read the history of a scratch board whose five closed tasks took known hours, through the estimation and recall scripts, and print `ok <case>` or
`fail <case>: <what it printed>` per case, then `PASS` or `FAIL`; exit 1 on any fail.

usage: replay-task-history.py
The tasks are filed and resolved by use-board.py, and their `createdAt` and `closedAt`, which the board stamps from the wall clock, are then set to times HOURS apart
in one commit on the board ref. A sixth task stays open, and a seventh, labelled LABEL, which no closed task has.
- durations: `list-task-durations.py` prints a row per closed task, oldest close first, with its start, end and hours from its creation, and `rows: 5 (pr 0, created 5)`
- estimate: `estimate-task-time.py` on the open task's url uses the default levels, since five tasks are too few to fit, prints the p10 and p90 of the five hours over five
  samples of the same first label, and a total between the least and the most hours
- fallback: the same script on the seventh task, whose first label too few past tasks share, prints the same p10 and p90 over all five past tasks, noted
  `all past tasks used`
- recall: `recall-work.py` with words of one closed task's title ranks that task first, as `#<n> task completed: <title>`, with its `REPORTED:` summary under it"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

KICK_OFF = pathlib.Path(__file__).resolve().parents[1]
BOARD = KICK_OFF / "scripts" / "use-board.py"
ESTIMATION = KICK_OFF / "references" / "estimation" / "scripts"
RECALL = KICK_OFF / "references" / "recall" / "scripts" / "recall-work.py"
REF = "refs/teamwork-blackboard"
TITLES = ("Probe the parser cache", "Probe the pane colours", "Probe the landing lock", "Probe the monitor clock", "Probe the export folder")
HOURS = (16, 1, 8, 2, 4)
START = datetime.datetime(2026, 1, 5, 9, tzinfo=datetime.timezone.utc)
RECALLED = 3  # the task whose title words `recall` asks by
LABEL = "area:new"


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def times(n):
    """(createdAt, closedAt) of closed task N, a day after the one before it."""
    created = START + datetime.timedelta(days=n - 1)
    return stamp(created), stamp(created + datetime.timedelta(hours=HOURS[n - 1]))


def quantile(values, level):
    """The LEVEL quantile of VALUES, interpolated between the two nearest ranks."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * level
    below = int(position)
    above = min(below + 1, len(ordered) - 1)
    return ordered[below] + (ordered[above] - ordered[below]) * (position - below)


def build(sandbox):
    """File and resolve the five tasks, file the open ones, and set the closed ones' times; the open tasks' urls."""
    body = replay_probe.write_text(sandbox.work, "body.md", replay_probe.BODY)
    for n, title in enumerate(TITLES, 1):
        filed = sandbox.python(BOARD, "file", "--title", title, "--body", body)
        resolved = sandbox.python(BOARD, "resolve", str(n), "--summary", f"Summary of {title.lower()}.")
        if filed.returncode or resolved.returncode:
            raise RuntimeError(f"filing or resolving {title!r}: {filed.stdout}{filed.stderr}{resolved.stdout}{resolved.stderr}")
    opened = sandbox.python(BOARD, "file", "--title", "Probe the next step", "--body", body)
    labelled = sandbox.python(BOARD, "file", "--title", "Probe a new area", "--body", body, "--label", LABEL)
    if opened.returncode or labelled.returncode:
        raise RuntimeError(f"filing the open tasks: {opened.stderr}{labelled.stderr}")
    environment = {**sandbox.environment, "GIT_INDEX_FILE": str(sandbox.work / "board-index")}

    def git(*argv):
        return replay_probe.sh("git", *argv, cwd=sandbox.repository, environment=environment).stdout.strip()

    git("read-tree", REF)
    for n in range(1, len(TITLES) + 1):
        record = json.loads(git("show", f"{REF}:{n}/task.json"))
        record["createdAt"], record["closedAt"] = times(n)
        blob = git("hash-object", "-w", replay_probe.write_text(sandbox.work, f"task-{n}.json", json.dumps(record)))
        git("update-index", "--cacheinfo", f"100644,{blob},{n}/task.json")
    old = git("rev-parse", REF)
    sandbox.clock(stamp(START + datetime.timedelta(days=len(TITLES) + 1)))
    git("update-ref", REF, git("commit-tree", git("write-tree"), "-p", old, "-m", "Set the probe tasks' times"), old)
    sandbox.clock(None)
    return opened.stdout.strip(), labelled.stdout.strip()


def durations(sandbox, cases):
    done = sandbox.python(ESTIMATION / "list-task-durations.py")
    closes = sorted(range(1, len(TITLES) + 1), key=lambda n: times(n)[1])
    want = ["number\tlabels\tcriteria\tstart\tend\thours\tsource",
            *(f"{n}\t\t{replay_probe.BODY.count('[check]')}\t{times(n)[0]}\t{times(n)[1]}\t{HOURS[n - 1]:.1f}\tcreated" for n in closes),
            f"rows: {len(TITLES)} (pr 0, created {len(TITLES)}); hours run from the start source to the close"]
    cases.step("durations", done.returncode == 0 and done.stdout.splitlines() == want, f"exit {done.returncode}, printed {done.stdout!r}{done.stderr[-300:]}, wanted {want!r}")


def estimate(sandbox, cases, url, case="estimate", note="same first label"):
    done = sandbox.python(ESTIMATION / "estimate-task-time.py", url)
    lines = done.stdout.splitlines()
    open_number = url.rsplit("/", 1)[1]
    row = f"#{open_number}\t{quantile(HOURS, 0.1):.1f}\t{quantile(HOURS, 0.9):.1f}\t{len(HOURS)}\t{note}"
    total = next((line.split("\t") for line in lines if line.startswith("total\t")), None)
    bounded = total is not None and min(HOURS) <= float(total[1]) <= float(total[2]) <= max(HOURS) and total[3] == "1000 bootstrap sums over 1 tasks"
    cases.step(case, done.returncode == 0 and lines[:1] == ["levels p10-p90 per task, p10-p90 total (default: too few past tasks to fit)"] and row in lines and bounded,
               f"exit {done.returncode}, printed {done.stdout!r}{done.stderr[-300:]}, wanted the row {row!r} and a total within {min(HOURS)}-{max(HOURS)} h")


def recall(sandbox, cases):
    title = TITLES[RECALLED - 1]
    done = sandbox.python(RECALL, *title.split()[2:])
    lines = done.stdout.splitlines()
    want = [f"#{RECALLED} task completed: {title}", f"  REPORTED: Summary of {title.lower()}."]
    cases.step("recall", done.returncode == 0 and lines[:2] == want,
               f"exit {done.returncode}, printed {done.stdout!r}{done.stderr[-300:]}, wanted first {want!r}")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("task-history-") as work:
        sandbox = replay_probe.Sandbox(work)
        try:
            url, labelled = build(sandbox)
            durations(sandbox, cases)
            estimate(sandbox, cases, url)
            estimate(sandbox, cases, labelled, "fallback", "all past tasks used")
            recall(sandbox, cases)
        except RuntimeError as e:
            cases.step("board", False, str(e)[-400:])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
