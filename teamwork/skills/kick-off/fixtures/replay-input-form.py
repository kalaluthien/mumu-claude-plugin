#!/usr/bin/env python3
"""Replay malformed and good text and options through the board's write scripts on a scratch git board, printing `ok <case>`
or `fail <case>: <what it saw>` per case and exiting 1 on any failure. A refusing case passes when every write exits 2,
the message names a fix and the board is unchanged; an `unstored-` case when every write exits 2 saying nothing was written, the board unchanged;
an `accept-` case when every write exits 0 and the board changed. Cases:
- `fence-*`: a `teamwork` or a `decision` fence at a line's start in a filed body, a comment, a decision, a summary or an edited body;
- `option-*`: an `--asks` that names no owner, `--asks owner` with fewer than two `--option`, an option on a `REPORTED:`, a `--live-runs` that is no count;
- `keyword-*`: a keyword line that nearly opens a comment, opens a later line or belongs to another verb;
- `heading-*`: a section heading misspelt or repeated;
- `edit-*`: a diff or keyword line `edit-issue-body.py` is given;
- `unstored-*`: a holder's or a decider's name that board-record-schema.json refuses;
- `accept-*`: text and options that must still post, and `accept-scenarios`, the output of replay-team-scenarios.py holding only `ok` lines;
- `stored-decision`: a `decide` with `--one-way`, `--answers`, `--holders` and `--live-runs` keeps a `comments/<k>.json` whose keys the schema all names, and `read` shows each;
- `stored-question`: a `comment --asks owner` with two `--option` keeps them as `options`, and `read` numbers them and says the task waits on the owner;
- `url-names-task`: `read` and `comment` take the url `file` printed as they take the number.

usage: replay-input-form.py [--only <case>,...]"""
import difflib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(ROOT / "lib"))

BASE = "A summary.\n\n## Goal\n\nDo it.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n1. [check] **The probe works when it runs once**: `true` prints nothing.\n"
TEAMWORK = "\n```teamwork\nholders: a-worker\n```\n"
DECISION = "\n```decision\ndecision: ship it\ndecided by: a-worker\ndoor: two-way\n```\n"
BY = ("--by", "a-manager")
TWO = ("--option", "the first", "--option", "the second")
SCHEMA = json.loads((HERE.parent / "assets" / "board-record-schema.json").read_text())

# name -> (writes, fix): each write is (verb, text, option...) with verb file, comment, decide or resolve, (verb, None, word...) with verb hold or depend,
# or ("edit", before, after, keyword line); the message of a refusal holds FIX
REFUSED = {
    "fence-teamwork": ([("file", BASE + TEAMWORK), ("comment", "REPORTED: probe findings\n" + TEAMWORK), ("comment", "BLOCKED: which one?\n\n```teamwork\nasks: owner\n```\n"),
                        ("decide", "DECIDED: ship the probe today\n" + TEAMWORK, *BY), ("resolve", "REPORTED: probe landed\n" + TEAMWORK),
                        ("edit", BASE, BASE + TEAMWORK, "DECIDED: add a holder")], "`teamwork` fence"),
    "fence-decision": ([("file", BASE + DECISION), ("comment", "REPORTED: probe findings\n" + DECISION), ("decide", "DECIDED: ship it\n" + DECISION, *BY),
                        ("resolve", "REPORTED: probe landed\n" + DECISION), ("edit", BASE, BASE + DECISION, "DECIDED: add a decision")], "`decision` fence"),
    "option-asks-value": ([("comment", "BLOCKED: which one?\n", "--asks", "someone", *TWO)], "--asks owner"),
    "option-asks-no-option": ([("comment", "BLOCKED: which one?\n", "--asks", "owner")], "two answers"),
    "option-asks-one-option": ([("comment", "BLOCKED: which one?\n", "--asks", "owner", "--option", "the first")], "two answers"),
    "option-on-report": ([("comment", "REPORTED: probe findings\n", "--asks", "owner", *TWO), ("comment", "REPORTED: probe findings\n", *TWO)], "BLOCKED:"),
    "option-live-runs-word": ([("decide", "DECIDED: cap the live runs\n", *BY, "--live-runs", "many")], "--live-runs 12"),
    "keyword-lowercase": ([("comment", "blocked: which one?\n")], "BLOCKED"),
    "keyword-bare": ([("comment", "BLOCKED which one?\n")], "BLOCKED"),
    "keyword-bold": ([("comment", "**BLOCKED:** which one?\n")], "BLOCKED"),
    "keyword-later-line": ([("comment", "Waiting on the owner.\nBLOCKED: which one?\n")], "first line"),
    "keyword-other-verb": ([("comment", "DECIDED: ship the probe today\n"), ("decide", "BLOCKED: which one?\n", *BY), ("resolve", "DECIDED: closing it\n")], "first line"),
    "heading-misspelt": ([("file", BASE.replace("## Goal", "## goal")), ("file", BASE.replace("## Definition of done", "## Definition Of Done"))], "write exactly"),
    "heading-level": ([("file", BASE.replace("## Goal", "### Goal"))], "## Goal"),
    "heading-repeated": ([("file", BASE + "\n## Definition of done\n\n1. [check] **The probe works again when it runs twice**: `true`\n")], "keep one"),
    "edit-keyword-lowercase": ([("edit", BASE, BASE + "\nMore.\n", "decided: lower")], "DECIDED:"),
    "edit-keyword-empty": ([("edit", BASE, BASE + "\nMore.\n", "")], "DECIDED:"),
    "edit-keyword-free": ([("edit", BASE, BASE + "\nMore.\n", "add more text")], "DECIDED:"),
    "edit-keyword-two-lines": ([("edit", BASE, BASE + "\nMore.\n", "DECIDED: add more\nholders: oops")], "one line"),
}
UNSTORED = {
    "unstored-holders-capital": [("hold", None, "A-Worker"), ("decide", "DECIDED: ship the probe today\n", *BY, "--holders", "A-Worker")],
    "unstored-holders-comma": [("decide", "DECIDED: ship the probe today\n", *BY, "--holders", "a-worker, b-worker")],
    "unstored-by-spaces": [("decide", "DECIDED: ship the probe today\n", "--by", "A Manager")],
}
ACCEPTED = {
    "accept-clean-comment": [("comment", "REPORTED: probe findings\n"), ("comment", "BLOCKED: which one?\n"), ("comment", "BLOCKED: which one?\n", *TWO)],
    "accept-other-fence": [("comment", "REPORTED: probe findings\n\n```yaml\nholders: a-worker\n```\n\nThe `teamwork` fence is gone.\n"), ("file", BASE + "\n```text\ndecision: none\n```\n")],
    "accept-clean-edit": [("edit", BASE, BASE + "\nMore.\n", "DECIDED: add more")],
    "accept-fixing-edit": [("edit", BASE + TEAMWORK, BASE, "DECIDED: drop the fence"), ("edit", BASE + TEAMWORK, BASE + TEAMWORK + "\nMore.\n", "DECIDED: add more beside the fence")],
    "accept-every-option": [("file", BASE), ("file", BASE, "a-label", "--scope", "", "--depends", "1"), ("comment", "BLOCKED: which one?\n", "--asks", "owner", *TWO),
                            ("decide", "DECIDED: ship the probe today\n", *BY, "--one-way", "--holders", "a-worker b-worker", "--live-runs", "2"),
                            ("decide", 'DECIDED: ship the probe today\n\nThe owner said "ship it".\n', "--by", "owner"),
                            ("hold", None, "a-worker", "b-worker"), ("hold", None), ("depend", None, "1"), ("depend", None, "#1")],
    "accept-keyword-spaced": [("comment", " REPORTED: probe findings\n"), ("decide", "\n DECIDED: ship the probe today\n", *BY), ("resolve", " REPORTED: done\n")],
    "accept-keyword-put-first": [("decide", "ship the probe today\n", *BY), ("resolve", "the probe landed\n")],
}
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    only = args[1].split(",") if args[:1] == ["--only"] and len(args) == 2 else None
    if args and only is None:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="input-form-"))
    repository = work / "repo"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"))
    os.chdir(repository)
    import board
    import board_git
    counter = iter(range(10 ** 6))

    def snapshot():
        return [(each["number"], each["body"], each["state"], each["depends"], [(note["body"], note.get("fields")) for note in each["comments"]]) for each in board_git.issues("all")]

    def prepare(spec):
        """The issue SPEC writes to, filed straight on the board so even a body the guard refuses is there; its number, None for a `file`."""
        return board_git.file("A task", spec[1] if spec[0] == "edit" else BASE, []) if spec[0] != "file" else None

    def written(text):
        path = work / f"text-{next(counter)}.md"
        path.write_text(text)
        return path

    def use(*argv):
        return subprocess.run([sys.executable, str(SCRIPTS / "use-board.py"), *map(str, argv)], capture_output=True, text=True)

    def write(spec, number):
        """Runs one write SPEC on the board; the completed process."""
        verb, *rest = spec
        if verb == "edit":
            before, after, line = rest
            diff = work / f"edit-{next(counter)}.diff"
            diff.write_text("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), "a/body", "b/body")))
            return subprocess.run([sys.executable, str(SCRIPTS / "edit-issue-body.py"), str(number), str(diff), line, "--base", board.body_sha(before)], capture_output=True, text=True)
        text, *options = rest
        return use(*(["file", "A task"] if verb == "file" else [verb, number]), *([] if text is None else [written(text)]), *options)

    def run(name, writes, holds):
        """Runs each of WRITES; HOLDS(done, changed) says whether one went as the case wants."""
        if only and name not in only:
            return
        seen = []
        for spec in writes:
            number = prepare(spec)
            before = snapshot()
            done = write(spec, number)
            changed = snapshot() != before
            seen += [] if holds(done, changed) else [f"{' '.join(map(str, spec[:1] + spec[2:]))}: exit {done.returncode}, board changed {changed}: {done.stdout}{done.stderr}"]
        step(name, not seen, "; ".join(seen))

    def stored(number, position):
        """The record the board keeps as NUMBER's comment at POSITION, as its file holds it."""
        shown = subprocess.run(["git", "show", f"{board_git.REF}:{number}/comments/{position:04d}.json"], capture_output=True, text=True)
        return json.loads(shown.stdout or "{}")

    def stored_decision():
        number = board_git.file("A task", BASE, [])
        question = use("comment", number, written("BLOCKED: which one?\n")).stdout.strip()
        decided = use("decide", number, written("DECIDED: ship the probe today\n\nIt is ready.\n"), *BY, "--one-way", "--answers", question, "--holders", "a-worker b-worker", "--live-runs", "2")
        url, record, read = decided.stdout.strip(), stored(number, 2), use("read", number).stdout
        wanted = {"text": "DECIDED: ship the probe today\n\nIt is ready.\n", "decision": "ship the probe today", "by": "a-manager", "one_way": True, "answers": question,
                  "holders": ["a-worker", "b-worker"], "live_runs": 2}
        shows = ["state: OPEN, held\n", "holders: a-worker b-worker\n", "binding decisions: 1\n", f"- #{number} a-manager, one-way: ship the probe today ({url}); answers {question}\n", "open questions: 0\n",
                 f"--- {url} (by: a-manager; answers: {question}; one way; holders: a-worker b-worker; live runs: 2)\n"]
        step("stored-decision", decided.returncode == 0 and record == wanted and set(record) <= set(SCHEMA["properties"]) and all(line in read for line in shows),
             f"exit {decided.returncode} {decided.stderr}\n{record}\n{[line for line in shows if line not in read]}\n{read}")

    def stored_question():
        number = board_git.file("A task", BASE, [])
        asked = use("comment", number, written("BLOCKED: which one?\n"), "--asks", "owner", *TWO)
        url, record, read = asked.stdout.strip(), stored(number, 1), use("read", number).stdout
        shows = ["state: OPEN, waits on the owner\n", "open questions: 1\n", f"- #{number} to the owner: which one? ({url})\n", f"--- {url} (asks: owner)\nBLOCKED: which one?\n\n1. the first\n2. the second\n"]
        step("stored-question", asked.returncode == 0 and record == {"text": "BLOCKED: which one?\n", "asks": "owner", "options": ["the first", "the second"]}
             and set(record) <= set(SCHEMA["properties"]) and all(line in read for line in shows), f"exit {asked.returncode} {asked.stderr}\n{record}\n{[line for line in shows if line not in read]}\n{read}")

    def url_names_task():
        filed = use("file", "A task", written(BASE))
        url = filed.stdout.strip()
        number = int(url.rsplit("/", 1)[1])
        posted = use("comment", url, written("REPORTED: probe findings\n"))
        held = use("hold", url, "a-worker")
        by_url, by_number = use("read", url), use("read", number)
        step("url-names-task", url.startswith("git+file://") and posted.stdout.strip() == f"{url}#comment-1" and held.stdout.strip() == f"{url}#comment-2"
             and by_url.returncode == 0 and by_url.stdout == by_number.stdout and f"#{number} A task\n" in by_url.stdout and "REPORTED: probe findings" in by_url.stdout
             and "holders: a-worker\n" in by_url.stdout, f"{url}\n{posted.stdout}{posted.stderr}{held.stdout}{held.stderr}{by_url.stdout}{by_url.stderr}")

    for name, (writes, fix) in REFUSED.items():
        run(name, writes, lambda done, changed, fix=fix: done.returncode == 2 and fix.lower() in done.stderr.lower() and not done.stdout and not changed)
    for name, writes in UNSTORED.items():
        run(name, writes, lambda done, changed: done.returncode == 2 and "nothing written" in done.stderr and not done.stdout and not changed)
    for name, writes in ACCEPTED.items():
        run(name, writes, lambda done, changed: done.returncode == 0 and changed)
    for name, case in (("stored-decision", stored_decision), ("stored-question", stored_question), ("url-names-task", url_names_task)):
        if not only or name in only:
            case()
    if not only or "accept-scenarios" in only:
        replay = subprocess.run([sys.executable, str(HERE / "replay-team-scenarios.py")], capture_output=True, text=True, timeout=900)
        stray = [line for line in (replay.stdout + replay.stderr).splitlines() if line.strip() and not line.startswith("ok ")]
        step("accept-scenarios", not stray and replay.returncode == 0, "\n".join(stray) or f"exit {replay.returncode}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
