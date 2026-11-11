#!/usr/bin/env python3
"""Replay what the issues pane shows of a waiting task, on a temporary git board written by use-board.py and read as the pane reads it
(list-issue-board.py --json), and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail.
- team-question: a question to the manager gives the row no wait, and its note is among the dim lines;
- owner-question: a question to the owner gives `waits on the owner`, its note is not dim, and the row lists its options numbered only once opened;
- owner-first: a task that is blocked by another and asks the owner still waits on the owner;
- parts: a parent whose every open part is blocked shows no wait;
- two-questions: with two questions to the owner open, the opened row lists each question again above its own numbered options;
- answered: once the owner's answer to one is recorded its options are gone and the other's stay;
- sorted: the task that waits on the owner is the board's first root;
- one-kind: the pane's code, the lister and the grammar name no wait on the manager and no wait on parts.

usage: replay-wait-kinds.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `echo ok` prints `ok`; on base nothing.\n")
OWNER = "waits on the owner"
GONE = ("waits on the manager", "waits on its parts")
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:600]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="wait-kinds-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")

    def use(*argv, text=None):
        if text is not None:
            (work / "text.md").write_text(text)
        done = subprocess.run([sys.executable, str(USE), *[str(work / "text.md") if word == "<file>" else str(word) for word in argv]], cwd=repository, capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(f"replay-wait-kinds: use-board.py {argv[0]} failed: {done.stderr}")
        return done.stdout.strip()

    def rows():
        listed = json.loads(subprocess.run([sys.executable, str(LIST), "", "--json", "--width", "60"], cwd=repository, capture_output=True, text=True).stdout or "[]")
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
        use("file", title, "<file>", text=BODY)
    use("file", "Do the blocked part", "<file>", "--depends", "4", text=BODY)
    use("hold", 1, "probe-worker")
    use("comment", 1, "<file>", text="BLOCKED: which cache does the probe read?\n")
    team = row(1)
    folded, opened, dim = notes(team)
    step("team-question", team["wait"] == "" and folded == ["? which cache does the probe read?"] and folded[0] in dim and not any("waits" in line for line in team["lines"]["status"]), team)

    question = use("comment", 2, "<file>", "--asks", "owner", "--option", "print it in lower case", "--option", "print it in capitals", text="BLOCKED: which case does the probe print?\n")
    owned = row(2)
    folded, opened, dim = notes(owned)
    step("owner-question", owned["wait"] == OWNER and folded == ["? which case does the probe print?"] and folded[0] not in dim
         and opened[:2] == ["1. print it in lower case", "2. print it in capitals"] and OWNER in " ".join(owned["lines"]["status"]), owned)
    step("sorted", rows()[0]["number"] == 2, [found["number"] for found in rows()])

    early = use("comment", 5, "<file>", "--asks", "owner", "--option", "yes", "--option", "no", text="BLOCKED: may the part start early?\n")
    step("owner-first", row(5)["wait"] == OWNER and row(5)["options"] == [["yes", "no"]], row(5))

    (work / "old.md").write_text(BODY)
    (work / "new.md").write_text(BODY + "2. [task] #5 Do the blocked part\n")
    (work / "parts.diff").write_text(subprocess.run(["diff", "-u", str(work / "old.md"), str(work / "new.md")], capture_output=True, text=True).stdout)
    sha = next(line.split(": ", 1)[1] for line in use("read", 3).splitlines() if line.startswith("body sha: "))
    use("edit", 3, work / "parts.diff", "DECIDED: adds the blocked part.", "--base", sha)
    use("decide", 5, "<file>", "--by", "owner", "--answers", early, text='DECIDED: the part starts after its blocker.\n\nOwner said: "no, after it".\n')
    parent = row(3)
    step("parts", parent["wait"] == "" and row(5)["wait"] == "" and not any("waits" in line for line in parent["lines"]["status"] + row(5)["lines"]["status"]), [parent, row(5)])

    use("comment", 2, "<file>", "--asks", "owner", "--option", "today", "--option", "tomorrow", text="BLOCKED: when does the probe run?\n")
    folded, opened, dim = notes(row(2))
    step("two-questions", folded == ["? which case does the probe print?", "? when does the probe run?"]
         and opened[:6] == [folded[0], "1. print it in lower case", "2. print it in capitals", folded[1], "1. today", "2. tomorrow"], row(2)["lines"])
    use("decide", 2, "<file>", "--by", "owner", "--answers", question, text='DECIDED: the probe prints in lower case.\n\nOwner said: "the first one".\n')
    after = row(2)
    folded, opened, dim = notes(after)
    step("answered", after["wait"] == OWNER and folded == ["? when does the probe run?"] and opened[:2] == ["1. today", "2. tomorrow"] and "1. print it in lower case" not in opened, after)

    pages = [ROOT / "hooks" / "draw-issue-pane.tsx", LIST, ROOT / "lib" / "issue_board.py", ROOT / "lib" / "issue_state.py", ROOT / "skills" / "kick-off" / "references" / "issue-grammar.md"]
    named = [f"{path.name}: {word}" for path in pages for word in GONE if word in path.read_text()]
    step("one-kind", not named, named)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
