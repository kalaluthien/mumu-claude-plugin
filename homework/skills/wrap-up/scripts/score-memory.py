#!/usr/bin/env python3
"""Score each candidate memory on dream's replay cases from its judges' verdicts, and print the one to keep.

usage: score-memory.py <dejavu>   reads <dejavu>/friction.jsonl, each candidate folder <dejavu>/candidates/<name>/,
                                  `current` among them, and its verdicts <dejavu>/judgements/<name>/*.jsonl, one file
                                  per judge

A verdict line is {"case": "<id>", "covered": true|false, "misfire": true|false}; the last one for a case counts. The
tuning score is covered cases minus misfires minus LOAD_COST per index line (`- [` lines of every MEMORY.md in the
candidate), since each line loads into every session. The highest tuning score is selected, `current` on a tie; a
selection whose held-out covered minus misfires falls below current's is rejected for current, since it fits only the
cases it was written from. A case with no verdict counts as not covered, and prints as `missing: <name> <n>`.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_cases  # noqa: E402

LOAD_COST = 0.1


def index_lines(candidate):
    return sum(line.startswith("- [") for index in sorted(candidate.rglob("MEMORY.md"))
               for line in index.read_text(encoding="utf-8").splitlines())


def verdicts(folder):
    found = {}
    lines = []
    for path in sorted(folder.glob("*.jsonl")):
        try:
            lines += path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and "case" in item:
            found[str(item["case"])] = (bool(item.get("covered")), bool(item.get("misfire")))
    return found


def score(candidate, judgements, cases):
    found = verdicts(judgements)
    row = {"name": candidate.name, "lines": index_lines(candidate),
           "missing": sum(item["id"] not in found for item in cases)}
    for split, held in (("tuning", False), ("held", True)):
        picked = [found.get(item["id"], (False, False)) for item in cases if item["held_out"] == held]
        row[split + "_covered"] = sum(covered for covered, _ in picked)
        row[split + "_misfires"] = sum(misfire for _, misfire in picked)
    row["tuning"] = round(row["tuning_covered"] - row["tuning_misfires"] - LOAD_COST * row["lines"], 2)
    row["held"] = row["held_covered"] - row["held_misfires"]
    return row


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    dejavu = pathlib.Path(args[0])
    cases = replay_cases.load(dejavu)
    folders = sorted(path for path in (dejavu / "candidates").glob("*") if path.is_dir())
    if not cases or "current" not in {path.name for path in folders}:
        print(f"score-memory: {dejavu} needs friction.jsonl and candidates/current/", file=sys.stderr)
        return 1
    rows = [score(path, dejavu / "judgements" / path.name, cases) for path in folders]
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
    best = max(rows, key=lambda row: row["tuning"])
    if best["tuning"] <= current["tuning"]:
        best = current
    if best["held"] < current["held"]:
        print(f"rejected: {best['name']} held-out {best['held']} below current {current['held']}")
        best = current
    print(f"selected: {best['name']}")
    if best is current:
        print("Keep the memory as it is: no candidate beat it on the tuning cases without losing held-out ones.")
    else:
        print(f"Copy the files {best['name']} changed back into the memory home: it covers more owner corrections "
              "for what it loads, and holds on the held-out cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
