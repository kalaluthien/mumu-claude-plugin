#!/usr/bin/env python3
"""List the owner's preferences that show in more than one of habit's mapped sessions, one line each, details below it.

usage: list-habits.py <data> [--groups <file>]
       list-habits.py <data> --record <where> <last seen> <name>   record where a preference went (a file, a url, a session, `owner` or `dropped`) in <data>/kept.json

Reads <data>/stats/ and <data>/facets/ for the sessions of the last 28 days and writes <data>/habits.jsonl, every habit
item with an id, for the agent that groups them. With --groups (`[{"name", "ids"}]`), a group of items in 2+ sessions
prints as `preference <n> sessions, <r> repos, last <date>[, kept <where>[, seen since]]: <name>`, then its kinds, its
examples, up to 3 quotes and any memory line already naming it.

`kept <where>` names where <data>/kept.json records the preference went; `seen since` means the owner showed it again
after the record's last sighting, so its kept form did not reach the agent and needs a stronger one.
"""
import collections
import glob
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import repeats  # noqa: E402
import transcript  # noqa: E402

WINDOW_DAYS, QUOTES = 28, 3


def main(args):
    if len(args) == 5 and args[1] == "--record":
        repeats.record(os.path.join(args[0], "kept.json"), args[2], float(args[3]), args[4])
        return 0
    if len(args) not in (1, 3) or args[0].startswith("-") or (len(args) == 3 and args[1] != "--groups"):
        print(__doc__, file=sys.stderr)
        return 2
    data, now = args[0], time.time()
    kept = repeats.load(os.path.join(data, "kept.json"), {})
    items = []
    for path in sorted(glob.glob(os.path.join(glob.escape(data), "stats", "*.json"))):
        row = repeats.load(path, None)
        if not (row and row.get("end") and row["end"] >= now - WINDOW_DAYS * 86400 and transcript.find(row["path"])):
            continue
        session = os.path.basename(path)[:-5]
        facet = repeats.load(os.path.join(data, "facets", f"{session}.json"), None) or {}
        for k, item in enumerate(facet.get("habits") or []):
            items.append(dict(item, id=f"{session[:8]}-{k}", session=session, path=row["path"], time=row["end"], repo=row["repo"]))
    with open(os.path.join(data, "habits.jsonl"), "w", encoding="utf-8") as out:
        out.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in items)

    by_id = {item["id"]: item for item in items}
    for group in repeats.load(args[2], []) if len(args) == 3 else []:
        found = [by_id[item_id] for item_id in group.get("ids") or [] if item_id in by_id]
        if len({item["path"] for item in found}) < 2:
            continue
        sightings = [(item["time"], item["path"], item.get("line") or 0, item["repo"]) for item in found]
        repeats.show("preference", group["name"], sightings, kept, "kept")
        kinds = collections.Counter(str(item.get("kind")) for item in found)
        print("  kinds " + ", ".join(f"{kind} {n}" for kind, n in kinds.most_common()))
        for item in sorted(found, key=lambda item: -item["time"])[:QUOTES]:
            print(f"  quote {item['id']}: {str(item.get('quote', ''))[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
