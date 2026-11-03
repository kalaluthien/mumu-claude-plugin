#!/usr/bin/env python3
"""Score each candidate memory on dream's replay cases from its picks and their marks, and print the one to keep.

usage: score-memory.py <dejavu>   reads <dejavu>/friction.jsonl, each candidate folder <dejavu>/candidates/<name>/,
                                  `current` among them, its picks <dejavu>/picks/<name>/*.jsonl and the marks
                                  <dejavu>/marks/*.jsonl

A case is covered for a candidate when the instruction files' mark or its recalled set's mark is covered, so a lesson
copied from the instruction files gains nothing; it misfires when its set's mark does. The tuning score is covered cases
minus misfires minus LOAD_COST per index line (`- [` lines of every MEMORY.md in the candidate), since each line loads
into every session. A candidate whose held-out covered minus misfires falls below current's is rejected, since it fits
only the cases it was written from; of the rest the highest tuning score is selected, `current` on a tie. A case with
no pick or no mark counts as not covered, and prints as `missing: <name> <n>`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_cases  # noqa: E402

LOAD_COST = 0.1


def index_lines(candidate):
    return sum(line.startswith("- [") for index in sorted(candidate.rglob("MEMORY.md"))
               for line in index.read_text(encoding="utf-8").splitlines())


def verdict(candidate, files, case, marked):
    """(covered, misfire, missing) of one case for one candidate."""
    if files is None:
        return False, False, True
    instructions = marked.get((case, replay_cases.INSTRUCTIONS))
    key = replay_cases.recall_set(candidate, files)
    own = marked.get((case, key)) if key else (False, False)
    missing = instructions is None or own is None
    covered = bool(instructions and instructions[0]) or bool(own and own[0])
    return covered, bool(own and own[1]), missing


def score(candidate, dejavu, cases, marked):
    found = replay_cases.picks(dejavu, candidate.name)
    row = {"name": candidate.name, "lines": index_lines(candidate), "missing": 0}
    for split, held in (("tuning", False), ("held", True)):
        row[split + "_covered"] = row[split + "_misfires"] = 0
        for item in cases:
            if item["held_out"] == held:
                covered, misfire, missing = verdict(candidate, found.get(item["id"]), item["id"], marked)
                row[split + "_covered"] += covered
                row[split + "_misfires"] += misfire
                row["missing"] += missing
    row["tuning"] = round(row["tuning_covered"] - row["tuning_misfires"] - LOAD_COST * row["lines"], 2)
    row["held"] = row["held_covered"] - row["held_misfires"]
    return row


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    dejavu = pathlib.Path(args[0])
    cases = replay_cases.load(dejavu)
    folders = replay_cases.candidates(dejavu)
    if not cases or "current" not in {path.name for path in folders}:
        print(f"score-memory: {dejavu} needs friction.jsonl and candidates/current/", file=sys.stderr)
        return 1
    marked = replay_cases.marks(dejavu)
    rows = [score(path, dejavu, cases, marked) for path in folders]
    rows.sort(key=lambda row: row["name"] != "current")
    print("| candidate | index lines | tuning covered | tuning misfires | tuning score | held-out covered | held-out misfires |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        print(f"| {row['name']} | {row['lines']} | {row['tuning_covered']} | {row['tuning_misfires']} | {row['tuning']} "
              f"| {row['held_covered']} | {row['held_misfires']} |")
    for row in rows:
        if row["missing"]:
            print(f"missing: {row['name']} {row['missing']}")
    current = rows[0]
    for row in rows:
        if row["held"] < current["held"]:
            print(f"rejected: {row['name']} held-out {row['held']} below current {current['held']}")
    best = current
    for row in rows:
        if row["held"] >= current["held"] and row["tuning"] > best["tuning"]:
            best = row
    print(f"selected: {best['name']}")
    if best is current:
        print("Keep the memory as it is: no candidate beat it on the tuning cases without losing held-out ones.")
    else:
        print(f"Copy the files {best['name']} changed back into the memory home: it covers more owner corrections "
              "for what it loads, and holds on the held-out cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
