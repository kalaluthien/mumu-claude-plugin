#!/usr/bin/env python3
"""Restore each lesson a dream's tidy took from a past owner correction that no other lesson still serves, then print
every correction and the dream's whole memory diff for the dream's review.

usage: restore-lessons.py <backup> <dejavu>

<backup> is the dream's backup of the day, each memory folder at its path below /; <dejavu> holds friction.jsonl, the
owner corrections the map found. A correction is served by an index line of a MEMORY.md that shares at least two content
words with its quote and what went wrong. A correction some index line served in the backup and none serves now gets
each of those lessons back: the backed-up file and its index line, in place of what the tidy left. It prints `restored
<file> for <correction id>` per lesson put back, a count line, `correction <id>: ...` per correction, then the unified
diff of each backed-up folder's files against the folder now; with no backup it prints `no backup at <backup>, nothing
checked` and changes nothing.
"""
import difflib
import json
import pathlib
import re
import shutil
import sys

SHARED_WORDS = 2  # one shared word matched most corrections to unrelated lessons in the owner's memory
STOP = set("""the a an and or of to in on for with by as at is are was were be been it its this that these those from
when then than what which who whose into onto not no but so do does did done has have had can could should would will
may might must each every any all one two own same such only also just very more most less over under after before
about again agent owner session sessions file files line lines memory read work while""".split())
LINK = re.compile(r"\]\(([^)]+)\)")


def words(text):
    return {word for word in re.findall(r"[a-z][a-z0-9-]{3,}", text.lower()) if word not in STOP}


def index_lines(folders):
    """(folder, file name, line) of each index line of each folder's MEMORY.md."""
    found = []
    for folder in folders:
        index = folder / "MEMORY.md"
        if index.is_file():
            for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
                link = LINK.search(line)
                if line.startswith("- [") and link:
                    found.append((folder, link.group(1), line))
    return found


def serving(correction, lines):
    asked = words(f"{correction.get('quote', '')} {correction.get('what_went_wrong', '')}")
    return [entry for entry in lines if len(asked & words(LINK.sub("]", entry[2]))) >= SHARED_WORDS]


def put_back(backup_folder, live_folder, name, line):
    """The backed-up lesson file and its index line, in place of what the tidy left of them."""
    if (backup_folder / name).is_file():
        (live_folder / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(backup_folder / name, live_folder / name)
    index = live_folder / "MEMORY.md"
    kept = index.read_text(encoding="utf-8").splitlines() if index.is_file() else ["# Memory index", ""]
    kept = [old for old in kept if not (LINK.search(old) and LINK.search(old).group(1) == name)]
    index.write_text("\n".join(kept + [line]) + "\n", encoding="utf-8")


def diff(backup_folder, live_folder):
    lines = []
    names = {path.name for path in backup_folder.glob("*.md")} | {path.name for path in live_folder.glob("*.md")}
    for name in sorted(names):
        before, after = backup_folder / name, live_folder / name
        old = before.read_text(encoding="utf-8", errors="replace").splitlines() if before.is_file() else []
        new = after.read_text(encoding="utf-8", errors="replace").splitlines() if after.is_file() else []
        lines += difflib.unified_diff(old, new, f"before/{live_folder / name}", f"after/{live_folder / name}", lineterm="")
    return lines


def main(args):
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    backup, dejavu = pathlib.Path(args[0]), pathlib.Path(args[1])
    backed_up = sorted({index.parent for index in backup.rglob("MEMORY.md")})
    if not backed_up:
        print(f"no backup at {backup}, nothing checked")
        return 0
    live = {folder: pathlib.Path("/") / folder.relative_to(backup) for folder in backed_up}
    corrections = []
    try:
        for row in (dejavu / "friction.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(row)
            except ValueError:
                continue
            if isinstance(item, dict) and item.get("id"):
                corrections.append(item)
    except OSError:
        pass
    before, restored = index_lines(backed_up), []
    for correction in corrections:
        served = serving(correction, before)
        if served and not serving(correction, index_lines(live.values())):
            for folder, name, line in served:
                put_back(folder, live[folder], name, line)
                restored.append(f"restored {live[folder] / name} for {correction['id']}")
    print("\n".join(restored + [f"{len(restored)} lessons restored for {len(corrections)} corrections"]))
    for correction in corrections:
        print(f"correction {correction['id']}: {correction.get('what_went_wrong', '')} | owner: {correction.get('quote', '')}")
    print("diff of memory, before the dream to now:")
    for folder in backed_up:
        for line in diff(folder, live[folder]):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
