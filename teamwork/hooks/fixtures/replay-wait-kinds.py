#!/usr/bin/env python3
"""Replay what the tasks pane shows of a waiting task, on a temporary git board written by use-board.py and read as the pane reads it
(list-task-board.py --json), and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
- team-question: a question to the manager gives the row no wait, and its note is among the dim lines;
- owner-question: a question to the owner gives `waits on the owner`, its note is not dim, and the row lists its options numbered only once opened;
- owner-first: a task that is blocked by another and asks the owner still waits on the owner;
- parts: a parent whose every open part is blocked shows no wait;
- two-questions: with two questions to the owner open, the opened row lists each question again above its own numbered options;
- answered: once the owner's answer to one is recorded its options are gone and the other's stay;
- sorted: the task that waits on the owner is the board's first root.

usage: replay-wait-kinds.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
OWNER = "waits on the owner"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("wait-kinds-") as work:
        return replay(replay_probe.Sandbox(work, [replay_probe.agent("probe-worker", 2)]), work)


def replay(sandbox, work):
    cases = replay_probe.Cases()
    step = cases.step

    owner = sandbox.session("probe-manager", "no, after it", "the first one")

    def use(*argv, text=None):
        if text is not None:
            (work / "text.md").write_text(text)
        done = sandbox.python(USE, *[work / "text.md" if word == "<file>" else word for word in argv], **(owner if "owner" in argv else {}))
        if done.returncode:
            raise SystemExit(f"replay-wait-kinds: use-board.py {argv[0]} failed: {done.stderr}")
        return done.stdout.strip()

    def rows():
        listed = json.loads(sandbox.python(LIST, "", "--json", "--width", "60").stdout or "[]")
        flat = []
        while listed:
            row = listed.pop(0)
            flat.append(row)
            listed = row.get("tasks", []) + listed
        return flat

    def row(number):
        return next(found for found in rows() if found["number"] == number)

    def notes(found):
        """(the lines a folded row shows, the lines it adds once opened, the dim ones among all)."""
        lines = found["lines"]
        return lines["notes"][:lines["questions"]], lines["notes"][lines["questions"]:], [lines["notes"][k] for k in lines["quiet"]]

    for title in ("Ask the team", "Ask the owner", "Hold a parent", "Wait on a task"):
        use("file", "--title", title, "--body", "<file>", text=replay_probe.BODY)
    use("file", "--title", "Do the blocked part", "--body", "<file>", "--depends", "4", text=replay_probe.BODY)
    use("hold", 1, "--holders", "probe-worker")
    use("comment", 1, "--blocked", "which cache does the probe read?")
    team = row(1)
    folded, opened, dim = notes(team)
    step("team-question", team["wait"] == "" and folded == ["? which cache does the probe read?"] and folded[0] in dim and not any("waits" in line for line in team["lines"]["status"]), team)

    question = use("comment", 2, "--blocked", "which case does the probe print?", "--asks", "owner", "--option", "print it in lower case", "--option", "print it in capitals")
    owned = row(2)
    folded, opened, dim = notes(owned)
    step("owner-question", owned["wait"] == OWNER and folded == ["? which case does the probe print?"] and folded[0] not in dim
         and opened[:2] == ["1. print it in lower case", "2. print it in capitals"] and OWNER in " ".join(owned["lines"]["status"]), owned)
    step("sorted", rows()[0]["number"] == 2, [found["number"] for found in rows()])

    early = use("comment", 5, "--blocked", "may the part start early?", "--asks", "owner", "--option", "yes", "--option", "no")
    step("owner-first", row(5)["wait"] == OWNER and row(5)["options"] == [["yes", "no"]], row(5))

    (work / "new.md").write_text(replay_probe.BODY + "2. [task] #5 Do the blocked part\n")
    sha = next(line.split(": ", 1)[1] for line in use("read", 3).splitlines() if line.startswith("body sha: "))
    use("edit", 3, "--body", work / "new.md", "--reason", "adds the blocked part.", "--base", sha)
    use("decide", 5, "--decision", "the part starts after its blocker.", "--owner-said", "<file>", "--by", "owner", "--answers", early, text="no, after it\n")
    parent = row(3)
    step("parts", parent["wait"] == "" and row(5)["wait"] == "" and not any("waits" in line for line in parent["lines"]["status"] + row(5)["lines"]["status"]), [parent, row(5)])

    use("comment", 2, "--blocked", "when does the probe run?", "--asks", "owner", "--option", "today", "--option", "tomorrow")
    folded, opened, dim = notes(row(2))
    step("two-questions", folded == ["? which case does the probe print?", "? when does the probe run?"]
         and opened[:6] == [folded[0], "1. print it in lower case", "2. print it in capitals", folded[1], "1. today", "2. tomorrow"], row(2)["lines"])
    use("decide", 2, "--decision", "the probe prints in lower case.", "--owner-said", "<file>", "--by", "owner", "--answers", question, text="the first one\n")
    after = row(2)
    folded, opened, dim = notes(after)
    step("answered", after["wait"] == OWNER and folded == ["? when does the probe run?"] and opened[:2] == ["1. today", "2. tomorrow"] and "1. print it in lower case" not in opened, after)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
