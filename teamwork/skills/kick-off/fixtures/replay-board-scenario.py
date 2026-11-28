#!/usr/bin/env python3
"""File a root and a task, make the task the root's part by a body edit and the root wait on it by `depend`, set holders, ask by BLOCKED, answer by DECIDED, edit the
body and resolve the task, which closes the root, then retitle and reopen the root, add a follow-up part to it and resolve that, which closes the root again, file one more task and stop it,
writing only through use-board.py, and print after each step a `step <name>` line, the head of `use-board.py read` for each task it filed and the board `list-task-board.py` draws, numbers and urls replaced
by names, then each task's stored `state`, one of open, completed and stopped, so a change that moves the protocol shows in the text.
The board is a scratch repository whose holder is a live session of the fake herdr.

usage: replay-board-scenario.py"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
USE = HERE.parent / "scripts" / "use-board.py"
LIST = HERE.parents[2] / "hooks" / "list-task-board.py"
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import replay_probe  # noqa: E402
import usage_parser  # noqa: E402

names = {}  # the number each task got, by the name the output uses


def use(*argv, **options):
    done = box.python(USE, *map(str, argv), **options)
    if done.returncode:
        sys.exit(f"replay-board-scenario: use-board.py {' '.join(map(str, argv))}: {done.stderr.strip()}")
    return done.stdout.strip()


def text(name, body):
    return replay_probe.write_text(box.work, name, body)


def filed(name, title, body):
    names[int(use("file", "--title", title, "--body", text(name, body)).rsplit("/", 1)[1])] = name


def number(name):
    return next(task_number for task_number, known in names.items() if known == name)


def plain(out):
    """OUT with each url one word and each task number its name."""
    return re.sub(r"(#|parent: )(\d+)", lambda match: match.group(1) + names.get(int(match.group(2)), match.group(2)), re.sub(r"(?:https|(?:git\+)?file)://\S+", "<url>", out))


def show(step):
    print(f"step {step}")
    for task_number, name in sorted(names.items(), key=lambda item: item[1]):
        print(plain(use("read", task_number).split("\n\n", 1)[0]))
    print(plain(box.python(LIST, "").stdout.rstrip()))


def sha_of(name):
    return re.search(r"body sha: (\w+)", use("read", number(name))).group(1)


def body_of(name):
    return use("read", number(name), "--body") + "\n"


def link(name, added, why):
    """Appends ADDED to NAME's body through `use-board.py edit`, the one way a part is linked."""
    use("edit", number(name), "--body", text(f"{name}-link.md", body_of(name).rstrip("\n") + "\n" + added), "--reason", why, "--base", sha_of(name))


def main(args):
    global box
    usage_parser.parser(__doc__).parse_args(args)
    with replay_probe.scratch("board-scenario-") as work:
        box = replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 4)])
        filed("root", "Probe the board root", "Probe the board by a root.\n")
        filed("task", "Probe the board task", replay_probe.BODY)
        show("file")
        link("root", f"\n## Definition of done\n\n1. [task] #{number('task')} Probe the board task\n", "the task is the root's part")
        show("part")
        use("depend", number("root"), "--depends", number("task"))
        show("order")
        use("hold", number("task"), "--holders", "probe-worker")
        show("hold")
        use("label", number("task"), "--label", "probe")
        show("label-add")
        use("label", number("task"), "--label", "probe", "--remove")
        show("label-remove")
        asked = use("comment", number("task"), "--blocked", "which sample proves the probe", "--asks", "owner", "--option", "ok: the first", "--option", "no: the second")
        show("ask")
        owner, said = box.decider("owner", "use the first")
        use("decide", number("task"), "--decision", "use the first sample", *said, "--answers", asked, **owner)
        show("answer")
        use("edit", number("task"), "--body", text("edit.md", body_of("task").replace("Do it.", "Do it twice.")), "--reason", "probe the body edit", "--base", sha_of("task"))
        show("edit")
        use("resolve", number("task"), "--summary", "probe landed")
        show("resolve-task")
        use("title", number("root"), "--title", "Probe the board again")
        show("retitle")
        use("reopen", number("root"))
        show("reopen")
        filed("follow-up", "Probe the board follow-up", replay_probe.BODY)
        link("root", f"2. [task] #{number('follow-up')} Probe the board follow-up\n", "a follow-up part")
        show("part-again")
        use("resolve", number("follow-up"), "--summary", "follow-up landed")
        show("resolve-again")
        filed("stopped", "Probe the board stop", replay_probe.BODY)
        use("resolve", number("stopped"), "--summary", "not needed", "--not-planned")
        show("stop")
        stored = {name: json.loads(box.git("show", f"refs/teamwork-blackboard:{task_number}/task.json"))["state"] for task_number, name in names.items()}
        print("stored states: " + ", ".join(f"{name} {state}" for name, state in sorted(stored.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
