#!/usr/bin/env python3
"""List what repeats across dejavu's mapped sessions, one line per repeat, details indented below it.

usage: list-repeats.py <data> [--mistakes <file>]
       list-repeats.py <data> --record <where> <last seen> <key>   record where a repeat went (an issue url, a path or `owner`) in <data>/filed.json

Reads <data>/stats/ and <data>/facets/ for the sessions of the last 14 days and writes <data>/friction.jsonl, every
friction item with an id, for the agent that groups them. A repeat line reads
`<kind> <n> sessions, <r> repos, last <date>[, filed <where>[, seen since]]: <key>`:

- `tool`: a failure signature in 3+ sessions, seen in the last 3 days;
- `mistake`: a group of friction items from --mistakes (`[{"name", "ids"}]`) in 3+ sessions, seen in the last 3 days.

`filed <where>` names where <data>/filed.json records the repeat went; `seen since` means it was sighted after the
record's last sighting, so a closed hand-over needs doing again and an open one does not.
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

WINDOW_DAYS, ALIVE_DAYS = 14, 3


def main(args):
    if len(args) == 5 and args[1] == "--record" and args[3].replace(".", "", 1).isascii() and args[3].replace(".", "", 1).isdigit():
        repeats.record(os.path.join(args[0], "filed.json"), args[2], float(args[3]), args[4])
        return 0
    if len(args) not in (1, 3) or args[0].startswith("-") or (len(args) == 3 and args[1] != "--mistakes"):
        print(__doc__, file=sys.stderr)
        return 2
    data, now = args[0], time.time()
    filed = repeats.load(os.path.join(data, "filed.json"), {})
    stats = {}
    for path in glob.glob(os.path.join(glob.escape(data), "stats", "*.json")):
        row = repeats.load(path, None)
        if row and row.get("end") and row["end"] >= now - WINDOW_DAYS * 86400 and transcript.find(row["path"]):
            stats[os.path.basename(path)[:-5]] = row
    alive = now - ALIVE_DAYS * 86400

    tools = collections.defaultdict(list)
    for row in stats.values():
        for failure in row["failures"]:
            tools[failure["key"]].append((failure["time"] or row["end"], row["path"], failure["line"], row["repo"]))
    for key, sightings in sorted(tools.items(), key=lambda item: -len({sighting[1] for sighting in item[1]})):
        if len({sighting[1] for sighting in sightings}) >= 3 and max(sighting[0] for sighting in sightings) >= alive:
            repeats.show("tool", key, sightings, filed, "filed")

    items = []
    for session, row in stats.items():
        facet = repeats.load(os.path.join(data, "facets", f"{session}.json"), None)
        if not facet:
            continue
        for k, item in enumerate(repeats.facet_items(facet, "friction")):
            items.append(dict(item, id=f"{session[:8]}-{k}", session=session, path=row["path"], time=row["end"], repo=row["repo"]))
    with open(os.path.join(data, "friction.jsonl"), "w", encoding="utf-8") as out:
        out.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in items)

    by_id = {item["id"]: item for item in items}
    for group in repeats.load(args[2], []) if len(args) == 3 else []:
        found = [by_id[i] for i in group.get("ids") or [] if i in by_id]
        sightings = [(i["time"], i["path"], i.get("line") or 0, i["repo"]) for i in found]
        if len({sighting[1] for sighting in sightings}) >= 3 and max(sighting[0] for sighting in sightings) >= alive:
            repeats.show("mistake", group["name"], sightings, filed, "filed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
