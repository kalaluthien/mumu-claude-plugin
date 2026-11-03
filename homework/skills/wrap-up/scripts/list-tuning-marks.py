#!/usr/bin/env python3
"""List, for one candidate, the tuning cases its memory left uncovered or misfired on, the input of a revision.

usage: list-tuning-marks.py <dejavu> <candidate>   reads <dejavu>/friction.jsonl, <dejavu>/candidates/<candidate>/,
                                                   <dejavu>/picks/<candidate>/*.jsonl and <dejavu>/marks/*.jsonl; per
                                                   tuning case not covered, one `case <id> <uncovered|misfire|missing>
                                                   folder <folder>: <what went wrong> | owner: <quote> | recalled:
                                                   <file>...` line

Held-out cases never print, so the session revising from this list cannot fit them; a case the instruction files cover
is covered, so it never prints either.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_cases  # noqa: E402


def main(args):
    if len(args) != 2 or any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    dejavu, name = pathlib.Path(args[0]), args[1]
    candidate = dejavu / "candidates" / name
    if not candidate.is_dir():
        print(f"list-tuning-marks: {candidate} is no candidate folder", file=sys.stderr)
        return 1
    found = replay_cases.picks(dejavu, name)
    marked = replay_cases.marks(dejavu)
    counts = {"uncovered": 0, "misfire": 0, "missing": 0}
    for item in replay_cases.load(dejavu):
        if item["held_out"]:
            continue
        files = found.get(item["id"])
        covered, misfire, missing = replay_cases.verdict(candidate, files, item["id"], marked)
        if covered and not misfire:
            continue
        kind = "misfire" if misfire else "missing" if missing else "uncovered"
        counts[kind] += 1
        print(f"case {item['id']} {kind} folder {item['folder']}: {replay_cases.flat(item.get('what_went_wrong'))} | "
              f"owner: {replay_cases.flat(item.get('quote'))} | recalled: {' '.join(files or []) or '-'}")
    print(f"{counts['uncovered']} uncovered, {counts['misfire']} misfired and {counts['missing']} missing tuning cases "
          f"for {name}: an uncovered case asks for a lesson its index recalls at that moment, a misfire for a narrower "
          "or deleted entry, and a missing one for another round of judges before revising.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
