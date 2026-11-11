#!/usr/bin/env python3
"""Replay the answers a task's question gets on a temporary git board, written only by use-board.py and read as the issues pane reads it
(list-issue-board.py --json), and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
- answer-no-answers, answer-owner, answer-by-owner: a decision with no `--answers` clears a manager's question by a manager or the owner, and an owner's question by the owner
- answer-reposted: a decision naming the last of three identical asks clears all three
- answer-both: two different questions each need their own decision
- answer-signal: the decision touches the file the pane rereads on
- keep-other-question, keep-comment-only, keep-worker-decision, keep-event, keep-owner-by-manager: a decision naming another question, a report, a worker's own decision, a holders event, or a manager's decision on a question asked of the owner, leave the mark

usage: replay-wait-mark.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
BODY = f"## Goal\n\nProbe an answered question.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n{replay_probe.CHECK}"
failures = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:400]}", flush=True)
    if not ok:
        failures.append(name)


def use(*argv):
    done = subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"replay-wait-mark: use-board.py {argv[0]} failed: {done.stderr}")
    return done.stdout.strip()


def post(verb, number, text, *options):
    path = work / f"text-{time.monotonic_ns()}.md"
    path.write_text(text)
    return use(verb, number, path, *options)


def file(title):
    path = work / f"body-{time.monotonic_ns()}.md"
    path.write_text(BODY)
    return int(use("file", title, path).rsplit("/", 1)[1])


def ask(number, question, owner=False):
    return post("comment", number, f"BLOCKED: {question}\n", *(("--asks", "owner", "--option", "yes", "--option", "no") if owner else ()))


def decide(number, text, answers="", by="probe-manager"):
    return post("decide", number, f"DECIDED: {text}\n" + ("\n> the owner's words\n" if by == "owner" else ""), "--by", by, *(("--answers", answers) if answers else ()))


def row(number):
    """The pane row of task NUMBER, as list-issue-board.py --json prints it."""
    listed = json.loads(subprocess.run([sys.executable, str(LIST), "probe", "--json"], capture_output=True, text=True).stdout or "[]")
    return next((found for found in listed if found["number"] == number), {"wait": "no row", "questions": []})


def marks(number):
    found = row(number)
    return found["wait"], found["questions"]


def cleared(number):
    """Whether the pane draws no waiting mark and no question on task NUMBER."""
    wait, questions = marks(number)
    return wait not in ("waits on the owner", "waits on the manager") and questions == []


def signal_stamp():
    import team_signal  # read here, since it reads the config folder set in main when it loads
    return team_signal.stamp()


def cases():
    task = file("Probe a plain answer")
    ask(task, "which cache")
    step("keep-comment-only", marks(task)[0] == "waits on the manager", marks(task))
    post("comment", task, "REPORTED: probe findings\n")
    step("keep-comment-only-after", marks(task)[0] == "waits on the manager", marks(task))
    signal = signal_stamp()
    decide(task, "use the shared cache")
    step("answer-no-answers", cleared(task), marks(task))
    step("answer-signal", signal_stamp() > signal, f"stamp {signal} -> {signal_stamp()}")

    owned = file("Probe an owner's question")
    ask(owned, "may the sync run", owner=True)
    step("keep-owner", marks(owned)[0] == "waits on the owner", marks(owned))
    decide(owned, "run the sync", by="owner")
    step("answer-owner", cleared(owned), marks(owned))

    answered_by_owner = file("Probe an owner's decision")
    ask(answered_by_owner, "which cache")
    decide(answered_by_owner, "use the shared cache", by="owner")
    step("answer-by-owner", cleared(answered_by_owner), marks(answered_by_owner))

    own = file("Probe a worker's own decision")
    ask(own, "which cache")
    decide(own, "my design keeps one cache", by="probe-worker")
    step("keep-worker-decision", marks(own) == ("waits on the manager", ["which cache"]), marks(own))
    use("hold", own, "probe-worker")
    step("keep-event", marks(own) == ("waits on the manager", ["which cache"]), marks(own))

    to_owner = file("Probe a manager on an owner's ask")
    ask(to_owner, "may the sync run", owner=True)
    decide(to_owner, "run the sync")
    step("keep-owner-by-manager", marks(to_owner) == ("waits on the owner", ["may the sync run"]), marks(to_owner))

    again = file("Probe a reposted question")
    asks = [ask(again, "may the sync run") for _ in range(3)]
    decide(again, "run the sync", answers=asks[-1])
    step("answer-reposted", cleared(again), marks(again))

    two = file("Probe two questions")
    first, second = ask(two, "which width counts"), ask(two, "which height counts")
    decide(two, "any height counts", answers=second)
    step("keep-other-question", marks(two) == ("waits on the manager", ["which width counts"]), marks(two))
    decide(two, "24 to 80 columns count", answers=first)
    step("answer-both", cleared(two), marks(two))


def main(args):
    global work
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="wait-mark-"))
    os.environ.update({"HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "config"), **replay_probe.IDENTITY})
    subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
    os.chdir(work / "repo")
    cases()
    print("FAIL" if failures else "PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
