#!/usr/bin/env python3
"""Replay the answers a task's question gets on a temporary git board, written only by use-board.py and read as the tasks pane reads it
(list-task-board.py --json), and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
- answer-named, answer-owner, answer-by-owner: a decision naming a question with `--answers` clears it, a manager's by a manager or the owner, an owner's by the owner; keep-unnamed: a decision with no `--answers` clears none
- answer-reposted: a decision naming the last of three asks, each re-asked with `--again` the first, clears all three
- answer-both: two different questions each need their own decision
- answer-signal: the decision touches the file the pane rereads on
- keep-other-question, keep-comment-only, keep-worker-decision, keep-event, keep-owner-by-manager: a decision naming another question, a report, a worker's own decision, a holders event, or a manager's decision on a question asked of the owner, leave the mark, which is the open question alone for one the team answers and `waits on the owner` too for one asked of the owner

usage: replay-wait-mark.py"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
cases = replay_probe.Cases()


def use(*argv):
    done = sandbox.python(USE, *map(str, argv))
    if done.returncode:
        raise SystemExit(f"replay-wait-mark: use-board.py {argv[0]} failed: {done.stderr}")
    return done.stdout.strip()


def file(title):
    return int(use("file", "--title", title, "--body", replay_probe.write_text(sandbox.work, "body.md", replay_probe.BODY)).rsplit("/", 1)[1])


def ask(number, question, owner=False, again=""):
    return use("comment", number, "--blocked", question, *(("--asks", "owner", "--option", "yes", "--option", "no") if owner else ()), *(("--again", again) if again else ()))


def decide(number, text, answers="", by="probe-manager"):
    quote = replay_probe.write_text(sandbox.work, "quote.md", "> the owner's words\n")
    return use("decide", number, "--decision", text, *(("--text", quote) if by == "owner" else ()), "--by", by, *(("--answers", answers) if answers else ()))


def row(number):
    """The pane row of task NUMBER, as list-task-board.py --json prints it."""
    listed = json.loads(sandbox.python(LIST, "probe", "--json").stdout or "[]")
    return next((found for found in listed if found["number"] == number), {"wait": "no row", "questions": []})


def marks(number):
    found = row(number)
    return found["wait"], found["questions"]


def cleared(number):
    """Whether the pane draws no waiting mark and no question on task NUMBER."""
    wait, questions = marks(number)
    return wait == "" and questions == []


def signal_stamp():
    """The signal file's stamp, as the pane's lib reads it in the sandbox's environment."""
    return sandbox.evaluate("import team_signal; print(team_signal.stamp())")


def replay():
    task = file("Probe a plain answer")
    cache = ask(task, "which cache")
    cases.step("keep-comment-only", marks(task) == ("", ["which cache"]), marks(task))
    use("comment", task, "--reported", "probe findings")
    cases.step("keep-comment-only-after", marks(task) == ("", ["which cache"]), marks(task))
    decide(task, "use the shared cache")
    cases.step("keep-unnamed", marks(task) == ("", ["which cache"]), marks(task))
    signal = signal_stamp()
    decide(task, "use the shared cache", answers=cache)
    cases.step("answer-named", cleared(task), marks(task))
    cases.step("answer-signal", signal_stamp() > signal, f"stamp {signal} -> {signal_stamp()}")

    owned = file("Probe an owner's question")
    owned_ask = ask(owned, "may the sync run", owner=True)
    cases.step("keep-owner", marks(owned)[0] == "waits on the owner", marks(owned))
    decide(owned, "run the sync", by="owner", answers=owned_ask)
    cases.step("answer-owner", cleared(owned), marks(owned))

    answered_by_owner = file("Probe an owner's decision")
    by_owner_ask = ask(answered_by_owner, "which cache")
    decide(answered_by_owner, "use the shared cache", by="owner", answers=by_owner_ask)
    cases.step("answer-by-owner", cleared(answered_by_owner), marks(answered_by_owner))

    own = file("Probe a worker's own decision")
    ask(own, "which cache")
    decide(own, "my design keeps one cache", by="probe-worker")
    cases.step("keep-worker-decision", marks(own) == ("", ["which cache"]), marks(own))
    use("hold", own, "--holders", "probe-worker")
    cases.step("keep-event", marks(own) == ("", ["which cache"]), marks(own))

    to_owner = file("Probe a manager on an owner's ask")
    ask(to_owner, "may the sync run", owner=True)
    decide(to_owner, "run the sync")
    cases.step("keep-owner-by-manager", marks(to_owner) == ("waits on the owner", ["may the sync run"]), marks(to_owner))

    again = file("Probe a reposted question")
    first = ask(again, "may the sync run")
    asks = [first, ask(again, "may the sync run", again=first), ask(again, "may the sync run", again=first)]
    decide(again, "run the sync", answers=asks[-1])
    cases.step("answer-reposted", cleared(again), marks(again))

    two = file("Probe two questions")
    first, second = ask(two, "which width counts"), ask(two, "which height counts")
    decide(two, "any height counts", answers=second)
    cases.step("keep-other-question", marks(two) == ("", ["which width counts"]), marks(two))
    decide(two, "24 to 80 columns count", answers=first)
    cases.step("answer-both", cleared(two), marks(two))


def main(args):
    global sandbox
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("wait-mark-") as work:
        sandbox = replay_probe.Sandbox(work)
        replay()
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
