#!/usr/bin/env python3
"""List dream's replay cases, the moments before each owner correction dejavu recorded in every project, and batch them for the pick judges.

usage: list-replay-cases.py <dejavu>   one `case <id> <repo> <tuning|held-out> folder <memory folder|->: asked: <the
                                       person's last prompt> | then: <what the agent did after it>` line per case,
                                       oldest first, read from its transcript up to the owner's line, then
                                       `batch <k>: <id>...` lines of at most 10 cases, one judge per batch and candidate

A case line holds neither the owner's words nor what went wrong, since a judge who sees the answer picks memory to fit
it. The newest fifth is held out: a revision is written from the tuning cases' marks only, and its held-out score checks
that it did not fit the cases it was written from. The memory folder is the one under the memory home that loads for
the case's repository besides the home's own index; `-` when its transcript or folder is gone.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_cases  # noqa: E402

BATCH = 10


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_cases.load(args[0])
    for item in cases:
        split = "held-out" if item["held_out"] else "tuning"
        print(f"case {item['id']} {item.get('repo') or '-'} {split} folder {item['folder']}: {item['situation']}")
    for start in range(0, len(cases), BATCH):
        print(f"batch {start // BATCH + 1}: " + " ".join(item["id"] for item in cases[start:start + BATCH]))
    projects = len({item.get("repo") for item in cases})
    held = sum(item["held_out"] for item in cases)
    print(f"{len(cases)} cases from {projects} projects, {held} held out: give each batch to one pick judge per "
          "candidate, then mark what they picked by list-recall-sets.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
