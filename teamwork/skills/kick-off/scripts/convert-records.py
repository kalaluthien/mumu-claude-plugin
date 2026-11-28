#!/usr/bin/env python3
"""Convert every task and comment of this repository's board to the form whose records carry their kind, once, right after the merge that brought it.

usage: convert-records.py [--repository <folder>]

It saves the board's commit as `refs/teamwork-blackboard-backup/4`, refused when that ref names another commit, converts every record on a copy,
then swaps the copy in only while the board still names the commit it read. A task's state becomes open, completed or stopped; a comment gains its
kind, keyword line, author, time and own ref, its `Judge note:` paragraphs become its `judge_note`, its links become refs relative to the board, `answers` a list, and `one_way` goes.
Prints `converted <t> tasks and <c> comments` and exits 0, or `nothing to convert` when no record is in the old form; prints why
and exits 1, the board unchanged, when a converted record does not fit its type, the backup ref names another commit or
the board moved meanwhile; exits 2 for a call it cannot read.
Undo by `git update-ref refs/teamwork-blackboard refs/teamwork-blackboard-backup/4`. Standard library and the plugin's lib only, Python 3.9."""

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board_refs  # noqa: E402
import data_folder  # noqa: E402
import iso_time  # noqa: E402
import record_types  # noqa: E402
import task_state  # noqa: E402

REF, BACKUP = board_refs.REF, "refs/teamwork-blackboard-backup/4"
# the old form's judge note: a paragraph opening `Judge note:`, bold or after `DECIDED: `, which a worker's read left out
NOTE = re.compile(r"^(?:DECIDED: )?\**Judge note:\**.*?(?=\n\s*\n|\n```|\Z)\s*", re.M | re.S)
LABEL = re.compile(r"^(?:DECIDED: )?\**Judge note:\**\s*")
LINKS = ("again", "supersedes", "answers")
WRITER = {"GIT_AUTHOR_NAME": "teamwork", "GIT_AUTHOR_EMAIL": "teamwork@localhost", "GIT_COMMITTER_NAME": "teamwork", "GIT_COMMITTER_EMAIL": "teamwork@localhost"}


def git(common, *args, data=None, env=None):
    run = subprocess.run(["git", f"--git-dir={common}", *args], capture_output=True, input=data, env={**os.environ, **(env or {})})
    if run.returncode:
        raise RuntimeError(f"git {args[0]}: {run.stderr.decode(errors='replace').strip()}")
    return run.stdout.decode()


def files_at(common, tip):
    """{path: text} of every file in TIP's tree, read in one batch."""
    entries = [line.split("\t", 1) for line in git(common, "ls-tree", "-r", "-z", tip).split("\0") if line]
    output = subprocess.run(["git", f"--git-dir={common}", "cat-file", "--batch"], capture_output=True, check=True,
                            input="".join(f"{head.split()[2]}\n" for head, _ in entries).encode()).stdout
    found, at = {}, 0
    for _, path in entries:
        header_end = output.index(b"\n", at)
        size = int(output[at:header_end].split()[2])
        found[path] = output[header_end + 1:header_end + 1 + size].decode()
        at = header_end + 1 + size + 1
    return found


def added_times(common, tip):
    """{path: seconds} of the commit that first added each path, the time the old form read a comment's from when its task kept none."""
    times, seconds = {}, None
    for token in git(common, "log", "-z", "--format=%x01%ct", "--name-only", "--diff-filter=A", tip).split("\0"):
        if token.startswith("\x01"):
            seconds = int(token[1:])
        elif token:
            times[token.removeprefix("\n")] = seconds  # the log runs newest first, so the oldest add overwrites
    return times


def own_reports():
    """The (task, comment) pairs the old own-reports file says this project's manager posted."""
    path = data_folder.folder("own-reports") / "urls"
    return {board_refs.stored(line) for line in path.read_text().splitlines()} if path.exists() else set()


def task_of(path):
    """(scope folder, task number) of a record's path."""
    *scope, number = path.split("/comments/")[0].removesuffix("/task.json").split("/")
    return "/".join(scope), int(number)


def state_of(old):
    return "open" if old["state"] == "OPEN" else "stopped" if old.get("reason") == "NOT_PLANNED" else "completed"


def convert_task(old):
    return {**old, "state": state_of(old)}


def relative(value):
    return board_refs.relative(value)


def without_notes(text):
    """TEXT without its judge notes, as the old form's worker read gave it, and the notes' words."""
    notes = [LABEL.sub("", found.group(0)).strip() for found in NOTE.finditer(text)]
    return NOTE.sub(lambda found: "DECIDED:\n\n" if found.group(0).startswith("DECIDED: ") else "", text), "\n\n".join(notes)


def convert_comment(old, path, created, own):
    scope, number = task_of(path)
    position = int(path.rsplit("/", 1)[1].split(".")[0])
    fields = {key: value for key, value in old.items() if key not in ("text", "one_way")}
    fields.update({key: [relative(link) for link in ([value] if isinstance(value, str) else value)] if key == "answers" else relative(value)
                   for key, value in fields.items() if key in LINKS})
    said, note = without_notes(old["text"])
    fields.update({"judge_note": note} if note else {})
    author = old.get("by") or (f"{scope.split('/')[0]}-manager" if scope and (number, position) in own else "unknown")
    return record_types.Comment.parse(said, fields, author, created, f"{number}#comment-{position}").dump(path)


def convert(common, tip):
    """{path: new text} of every old-form record at TIP."""
    old = files_at(common, tip)
    times, own, changed = None, own_reports(), {}
    for path, text in old.items():
        if path.endswith("/task.json"):
            stored = json.loads(text)
            if stored.get("state") in ("OPEN", "CLOSED"):
                changed[path] = json.dumps(record_types.Task.load(convert_task(stored), path).dump(path))
        elif "/comments/" in path and "kind" not in (stored := json.loads(text)):
            home = path.split("/comments/")[0]
            given = json.loads(old[f"{home}/task.json"]).get("commentTimes", [])
            # ls-tree lists paths in order, so a comment's place among its task's is its place in OLD
            at = [name for name in old if name.startswith(f"{home}/comments/")].index(path)
            if at >= len(given) and times is None:
                times = added_times(common, tip)
            created = given[at] if at < len(given) else iso_time.stamp(times[path])
            changed[path] = json.dumps(convert_comment(stored, path, created, own), ensure_ascii=False, indent=1)
    return changed


def committed(common, tip, changed):
    """The commit of TIP's tree with CHANGED's files over it, built in an index of its own."""
    with tempfile.TemporaryDirectory() as folder:
        env = {"GIT_INDEX_FILE": str(pathlib.Path(folder) / "index"), **WRITER}
        texts = []
        for k, text in enumerate(changed.values()):
            texts.append(pathlib.Path(folder) / str(k))
            texts[-1].write_text(text)
        blobs = git(common, "hash-object", "-w", "--stdin-paths", data="".join(f"{path}\n" for path in texts).encode()).split()
        git(common, "read-tree", tip, env=env)
        git(common, "update-index", "--index-info", data="".join(f"100644 {blob}\t{path}\n" for blob, path in zip(blobs, changed)).encode(), env=env)
        tree = git(common, "write-tree", env=env).strip()
        return git(common, "commit-tree", tree, "-p", tip, "-m", "convert every record to the form whose records carry their kind", env=env).strip()


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    args = data_folder.enter(args, __doc__)
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    common = data_folder.common_folder()
    tip = subprocess.run(["git", f"--git-dir={common}", "rev-parse", "--verify", f"{REF}^{{commit}}"], capture_output=True, text=True).stdout.strip()
    if not tip:
        print(f"nothing to convert: this repository has no {REF}")
        return 0
    try:
        changed = convert(common, tip)
    except task_state.Refused as e:
        print(f"nothing was changed, since a converted record does not fit its type: {e}", file=sys.stderr)
        return 1
    if not changed:
        print("nothing to convert: every record is in the form whose records carry their kind")
        return 0
    backup = subprocess.run(["git", f"--git-dir={common}", "rev-parse", "--verify", BACKUP], capture_output=True, text=True).stdout.strip()
    if backup and backup != tip:
        print(f"{BACKUP} names {backup}, not the board's {tip}: it holds an earlier board, so nothing was changed; move it aside by `git update-ref -d {BACKUP}` once you no longer need it", file=sys.stderr)
        return 1
    if not backup:
        git(common, "update-ref", BACKUP, tip, "")
    try:
        git(common, "update-ref", "-m", "convert every record", REF, committed(common, tip, changed), tip)
    except RuntimeError as e:
        print(f"the board moved while it was converted, so it was left as it was: run this again ({e})", file=sys.stderr)
        return 1
    tasks = sum(path.endswith("/task.json") for path in changed)
    print(f"converted {tasks} tasks and {len(changed) - tasks} comments; {BACKUP} holds the board as it was")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
