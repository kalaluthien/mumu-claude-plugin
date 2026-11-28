#!/usr/bin/env python3
"""Count each shape of the board records still in the form before records carry their kind, so a fixture board can be checked to hold every shape a live board has.

usage: count-record-shapes.py [--repository <folder>]

Reads `refs/teamwork-blackboard` of the repository of the current folder, or of `--repository`, and prints `<count>\t<shape>` per shape, most first,
then `<n> shapes in <t> tasks and <c> comments`. A shape is a task's state, reason and how many comment times it keeps; a comment's set of keys;
the type of its `answers`; whether each link is a url; and the form of its text: its keyword line, a note's opening, a judge note's label.
A record already in the new form counts as no shape. Prints `no board` and exits 0 when the repository has no ref. Standard library only, Python 3.9."""

import collections
import json
import pathlib
import re
import subprocess
import sys

REF = "refs/teamwork-blackboard"
KEYWORD = re.compile(r"(BLOCKED|DECIDED|REPORTED):( ?)([^\n]*)(\n\n|\n|$)")
JUDGE_NOTE = re.compile(r"^(DECIDED: )?(\**)Judge note:", re.M)


def git(folder, *args, data=None):
    return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, check=True, input=data).stdout


def files(folder):
    """{path: text} of every task.json and comment of the board's tree."""
    tip = subprocess.run(["git", "-C", str(folder), "rev-parse", "-q", "--verify", f"{REF}^{{commit}}"], capture_output=True, text=True).stdout.strip()
    if not tip:
        return None
    paths = [line.split("\t", 1)[1] for line in git(folder, "ls-tree", "-r", "-z", tip).decode().split("\0") if line]
    paths = [path for path in paths if path.endswith("/task.json") or "/comments/" in path]
    output = git(folder, "cat-file", "--batch", data="".join(f"{tip}:{path}\n" for path in paths).encode())
    found, at = {}, 0
    for path in paths:
        header_end = output.index(b"\n", at)
        size = int(output[at:header_end].split()[2])
        found[path] = output[header_end + 1:header_end + 1 + size].decode()
        at = header_end + 1 + size + 1
    return found


def text_form(text):
    found = KEYWORD.match(text)
    if found:
        words = "words" if found.group(3).strip() else "no words"
        after = {"\n\n": "a blank line", "\n": "a newline", "": "the end"}[found.group(4)]
        return f"keyword with {words}{', a space' if found.group(2) else ''}, then {after}"
    return "note opening with a capitalised word and a colon" if re.match(r"\s*[A-Z]+:", text) else "note"


def shapes(records):
    counted = collections.Counter()
    comments = collections.defaultdict(int)
    for path in records:
        if "/comments/" in path:
            comments[path.split("/comments/")[0]] += 1
    for path, text in records.items():
        stored = json.loads(text)
        if path.endswith("/task.json"):
            if "reason" not in stored and "commentTimes" not in stored:
                continue
            times = stored.get("commentTimes")
            kept = "none" if times is None else "empty" if not times else "all" if len(times) >= comments[path.removesuffix("/task.json")] else "some"
            counted[f"task state {stored['state']}/{stored.get('reason') or ''}, comment times {kept}"] += 1
            continue
        if "kind" in stored:
            continue
        counted[f"comment keys {'+'.join(sorted(stored))}"] += 1
        if "answers" in stored:
            counted[f"comment answers as a {'list' if isinstance(stored['answers'], list) else 'string'}"] += 1
        for key in ("again", "supersedes", "answers"):
            for value in [stored[key]] if isinstance(stored.get(key), str) else stored.get(key) or []:
                counted[f"comment {key} as a {'url' if '://' in value else 'ref'}"] += 1
        counted[f"comment text {text_form(stored['text'])}"] += 1
        for label in JUDGE_NOTE.finditer(stored["text"]):
            counted[f"comment judge note {'after the keyword' if label.group(1) else 'bold' if label.group(2) else 'plain'}"] += 1
    return counted


def main(args):
    folder = pathlib.Path.cwd()
    if args[:1] == ["--repository"] and len(args) == 2:
        folder, args = pathlib.Path(args[1]), []
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    records = files(folder)
    if records is None:
        print("no board")
        return 0
    counted = shapes(records)
    for shape, count in sorted(counted.items(), key=lambda item: (-item[1], item[0])):
        print(f"{count}\t{shape}")
    tasks = sum(path.endswith("/task.json") for path in records)
    print(f"{len(counted)} shapes in {tasks} tasks and {len(records) - tasks} comments")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
