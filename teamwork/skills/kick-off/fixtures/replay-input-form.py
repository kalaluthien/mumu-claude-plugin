#!/usr/bin/env python3
"""Replay malformed and good text through the board's write scripts on a scratch git board, printing `ok <case>`
or `fail <case>: <what it saw>` per case and exiting 1 on any failure. A refusing case passes when every write exits 2,
the message names a fix and the board is unchanged; an `accept-` case when every write exits 0 and the board changed. Cases:
- `key-*`: a key line misspelt, holding more than names, or in a fence that is not exactly `teamwork`;
- `keyword-*`: a keyword line that nearly opens a comment, opens a later line or belongs to another verb;
- `heading-*`: a section heading misspelt or repeated;
- `edit-*`: a diff or keyword line `edit-issue-body.py` is given;
- `prose-*`: a plain line that opens with a key word, and the same words in a code span;
- `accept-*`: text that must still post, and `accept-scenarios`, the output of replay-team-scenarios.py holding only `ok` lines.

usage: replay-input-form.py [--only <case>,...]"""
import difflib
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(ROOT / "lib"))

BASE = "A summary.\n\n## Goal\n\nDo it.\n\n## Definition of done\n\n1. [check] **it works**: `true` prints nothing.\n"
FENCED = "\n```teamwork\n{}\n```\n"
STRAY = BASE + "\nholders: stray-worker\n"


def fenced(line):
    return BASE + FENCED.format(line)


# name -> (writes, fix): each write is (verb, text) with verb file, comment, decide or resolve, or ("edit", before, after, keyword line);
# the message of a refusal holds FIX
REFUSED = {
    "key-case": ([("file", fenced("Holders: a-worker")), ("comment", "REPORTED: x\n\nHolders: a-worker\n")], "holders"),
    "key-sign": ([("file", fenced("holders=a-worker")), ("comment", "REPORTED: x\n\nholders=a-worker\n")], "holders"),
    "key-singular": ([("file", fenced("holder: a-worker")), ("comment", "REPORTED: x\n\nholder: a-worker\n")], "holders"),
    "key-holders-spaces": ([("file", fenced("holders: A Worker")), ("comment", "DECIDED: x\n\n```teamwork\nholders: A Worker\n```\n")], "a-worker b-worker"),
    "key-holders-comma": ([("file", fenced("holders: a-worker, b-worker")), ("comment", "DECIDED: x\n\n```teamwork\nholders: a-worker, b-worker\n```\n")], "separated by spaces"),
    "key-asks-value": ([("file", fenced("asks: someone")), ("comment", "BLOCKED: which?\n\n```teamwork\nasks: someone\n```\n")], "asks: owner"),
    "key-fence-prose": ([("file", fenced("holders: a-worker\nthis is only prose")), ("comment", "REPORTED: x\n\n```teamwork\nnote to self\n```\n")], "key: value"),
    "key-fence-name": ([("file", BASE + "\n```Teamwork\nholders: a-worker\n```\n"), ("comment", "REPORTED: x\n\n```Teamwork\nholders: a-worker\n```\n")], "```teamwork"),
    "key-fence-yaml": ([("file", BASE + "\n```yaml\nholders: a-worker\n```\n"), ("comment", "REPORTED: x\n\n```yaml\nholders: a-worker\n```\n")], "```teamwork"),
    "keyword-lowercase": ([("comment", "blocked: which one?\n")], "BLOCKED"),
    "keyword-bare": ([("comment", "BLOCKED which one?\n")], "BLOCKED"),
    "keyword-bold": ([("comment", "**BLOCKED:** which one?\n")], "BLOCKED"),
    "keyword-later-line": ([("comment", "Waiting on the owner.\nBLOCKED: which one?\n")], "first line"),
    "keyword-other-verb": ([("decide", "BLOCKED: which one?\n"), ("resolve", "DECIDED: closing it\n")], "first word"),
    "heading-misspelt": ([("file", BASE.replace("## Goal", "## goal")), ("file", BASE.replace("## Definition of done", "## Definition Of Done"))], "write exactly"),
    "heading-level": ([("file", BASE.replace("## Goal", "### Goal"))], "## Goal"),
    "heading-repeated": ([("file", BASE + "\n## Definition of done\n\n1. [check] **again**: `true`\n")], "keep one"),
    "edit-stray-key": ([("edit", BASE, BASE + "\nholders: stray\n", "DECIDED: add a holder")], "teamwork"),
    "edit-keyword-lowercase": ([("edit", BASE, BASE + "\nMore.\n", "decided: lower")], "DECIDED:"),
    "edit-keyword-empty": ([("edit", BASE, BASE + "\nMore.\n", "")], "DECIDED:"),
    "edit-keyword-free": ([("edit", BASE, BASE + "\nMore.\n", "add more text")], "DECIDED:"),
    "edit-keyword-two-lines": ([("edit", BASE, BASE + "\nMore.\n", "DECIDED: add more\nholders: oops")], "one line"),
    "prose-key-refused": ([("comment", "REPORTED: x\n\nHolders: yes or no\n")], "code span"),
}
EVERY_KEY = "holders: a-worker b-worker\nasks: owner\ndepends on: #1 #2"
ACCEPTED = {
    "prose-code-span-accepted": [("comment", "REPORTED: x\n\n`Holders: yes or no`\n")],
    "accept-clean-comment": [("comment", "REPORTED: fine\n\n```teamwork\nholders: a-worker b-worker\n```\n")],
    "accept-clean-edit": [("edit", BASE, BASE + "\nMore.\n", "DECIDED: add more")],
    "accept-fixing-edit": [("edit", STRAY, BASE, "DECIDED: drop the stray line")],
    "accept-every-key": [("file", fenced(EVERY_KEY)), ("comment", f"BLOCKED: which?\n\n```teamwork\n{EVERY_KEY}\n```\n"),
                         ("decide", "DECIDED: x\n\n```decision\ndecision: ship it\ndecided by: a-worker\ndoor: two-way\n```\n")],
    "accept-keyword-spaced": [("comment", " DECIDED: x\n"), ("decide", "\n DECIDED: x\n"), ("resolve", " REPORTED: done\n")],
}
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()}", flush=True)
    failed.extend([] if ok else [name])


def main(args):
    only = args[1].split(",") if args[:1] == ["--only"] and len(args) == 2 else None
    if args and only is None:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="input-form-"))
    repo = work / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    os.environ.update(HOME=str(work), CLAUDE_CONFIG_DIR=str(work / "home"))
    os.chdir(repo)
    import board
    import board_git
    counter = iter(range(10 ** 6))

    def snapshot():
        return [(each["number"], each["body"], each["state"], [note["body"] for note in each["comments"]]) for each in board_git.issues("all")]

    def prepare(spec):
        """The issue SPEC writes to, filed straight on the board so even a body the guard refuses is there; its number, None for a `file`."""
        return board_git.file("A task", spec[1] if spec[0] == "edit" else BASE, []) if spec[0] != "file" else None

    def write(spec, number):
        """Runs one write SPEC on the board; the completed process."""
        verb, *rest = spec
        if verb == "edit":
            before, after, line = rest
            diff = work / f"edit-{next(counter)}.diff"
            diff.write_text("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), "a/body", "b/body")))
            return subprocess.run([sys.executable, str(SCRIPTS / "edit-issue-body.py"), str(number), str(diff), line, "--base", board.body_sha(before)], capture_output=True, text=True)
        text = work / f"text-{next(counter)}.md"
        text.write_text(rest[0])
        argv = ["file", "A task", text] if verb == "file" else [verb, number, text]
        return subprocess.run([sys.executable, str(SCRIPTS / "use-board.py"), *map(str, argv)], capture_output=True, text=True)

    def run(name, writes, fix=None):
        if only and name not in only:
            return
        seen = []
        for spec in writes:
            number = prepare(spec)
            before = snapshot()
            done = write(spec, number)
            changed = snapshot() != before
            held = done.returncode == 2 and fix.lower() in done.stderr.lower() and not changed if fix else done.returncode == 0 and changed
            seen += [] if held else [f"{spec[0]}: exit {done.returncode}, board changed {changed}: {done.stdout}{done.stderr}"]
        step(name, not seen, "; ".join(seen))

    for name, (writes, fix) in REFUSED.items():
        run(name, writes, fix)
    for name, writes in ACCEPTED.items():
        run(name, writes)
    if not only or "accept-scenarios" in only:
        replay = subprocess.run([sys.executable, str(HERE / "replay-team-scenarios.py")], capture_output=True, text=True, timeout=900)
        stray = [line for line in (replay.stdout + replay.stderr).splitlines() if line.strip() and not line.startswith("ok ")]
        step("accept-scenarios", not stray and replay.returncode == 0, "\n".join(stray) or f"exit {replay.returncode}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
