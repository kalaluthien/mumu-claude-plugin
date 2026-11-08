#!/usr/bin/env python3
"""List what recurs across mapped sessions, the agent's mistakes or the owner's preferences, one line each, details below it.

usage: list-repeats.py mistakes <data> [--sessions <map>] [--groups <file>]
       list-repeats.py habits <data> [--sessions <map>] [--groups <file>]
       list-repeats.py mistakes|habits <data> --record <where> <last seen> <key>   record where one went (a url, a
                                                                                   file, a session, `owner` or
                                                                                   `dropped`) in <data>/filed.json
                                                                                   or <data>/kept.json

With no `autoMemoryDirectory` in the global settings it exits 1 with a message naming the setting, before any output.
Reads <map>/stats/ and <map>/facets/, <map> being <data> unless given, for the sessions of the kind's window and writes
<data>/friction.jsonl or <data>/habits.jsonl, every item of the kind with an id, for the agent that groups them. With
--groups (`[{"name", "ids"}]`), each group in enough sessions prints. A line reads
`<label> <n> sessions, <r> repos, last <date>[, <went> <where>[, seen since]]: <key>`:

- mistakes, 14 days: `tool`, a failure signature in 3+ sessions, and `mistake`, a group of friction items in 3+
  sessions, each seen in the last 3 days; `<went>` is `filed`;
- habits, 28 days: `preference`, a group of habit items in 2+ sessions, then its kinds and up to 3 quotes; `<went>` is
  `kept`.

`seen since` means it was sighted after the record's last sighting, so its hand-over or kept form did not hold and needs
doing again, or a stronger one.
"""
import collections
import glob
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_home  # noqa: E402
import repeats  # noqa: E402
import transcript  # noqa: E402

KINDS = {
    "mistakes": {"days": 14, "sessions": 3, "alive_days": 3, "field": "friction", "items": "friction.jsonl",
                 "records": "filed.json", "went": "filed", "label": "mistake"},
    "habits": {"days": 28, "sessions": 2, "alive_days": None, "field": "habits", "items": "habits.jsonl",
               "records": "kept.json", "went": "kept", "label": "preference"},
}
QUOTES = 3


def recurs(sightings, kind, now):
    """Whether sightings, (time, session path, line, repo), span enough sessions and, for mistakes, are still alive."""
    alive = kind["alive_days"] is None or max(sighting[0] for sighting in sightings) >= now - kind["alive_days"] * 86400
    return len({sighting[1] for sighting in sightings}) >= kind["sessions"] and alive


def main(args):
    kind = KINDS.get(args[0]) if args else None
    rest = args[1:]
    if kind and len(rest) == 5 and rest[1] == "--record" and rest[3].replace(".", "", 1).isascii() and rest[3].replace(".", "", 1).isdigit():
        repeats.record(os.path.join(rest[0], kind["records"]), rest[2], float(rest[3]), rest[4])
        return 0
    options = dict(zip(rest[1::2], rest[2::2]))
    if not kind or not rest or rest[0].startswith("-") or len(rest) % 2 == 0 or not set(options) <= {"--sessions", "--groups"} or len(options) * 2 + 1 != len(rest):
        print(__doc__, file=sys.stderr)
        return 2
    memory_home.require()
    data, now = rest[0], time.time()
    sessions = options.get("--sessions", data)
    records = repeats.load(os.path.join(data, kind["records"]), {})
    stats = {}
    for path in sorted(glob.glob(os.path.join(glob.escape(sessions), "stats", "*.json"))):
        row = repeats.load(path, None)
        if row and row.get("end") and row["end"] >= now - kind["days"] * 86400 and transcript.find(row["path"]):
            stats[os.path.basename(path)[:-5]] = row

    if args[0] == "mistakes":
        tools = collections.defaultdict(list)
        for row in stats.values():
            for failure in row.get("failures") or []:
                tools[failure["key"]].append((failure["time"] or row["end"], row["path"], failure["line"], row["repo"]))
        for key, sightings in sorted(tools.items(), key=lambda item: -len({sighting[1] for sighting in item[1]})):
            if recurs(sightings, kind, now):
                repeats.show("tool", key, sightings, records, kind["went"])

    items = []
    for session, row in stats.items():
        facet = repeats.load(os.path.join(sessions, "facets", f"{session}.json"), None) or {}
        for k, item in enumerate(repeats.facet_items(facet, kind["field"])):
            items.append(dict(item, id=f"{session[:8]}-{k}", session=session, path=row["path"], time=row["end"], repo=row["repo"]))
    with open(os.path.join(data, kind["items"]), "w", encoding="utf-8") as out:
        out.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in items)

    by_id = {item["id"]: item for item in items}
    for group in repeats.load(options["--groups"], []) if "--groups" in options else []:
        found = [by_id[item_id] for item_id in group.get("ids") or [] if item_id in by_id]
        sightings = [(item["time"], item["path"], item.get("line") or 0, item["repo"]) for item in found]
        if not sightings or not recurs(sightings, kind, now):
            continue
        repeats.show(kind["label"], group["name"], sightings, records, kind["went"])
        if args[0] == "habits":
            kinds = collections.Counter(str(item.get("kind")) for item in found)
            print("  kinds " + ", ".join(f"{name} {n}" for name, n in kinds.most_common()))
            for item in sorted(found, key=lambda item: -item["time"])[:QUOTES]:
                print(f"  quote {item['id']}: {str(item.get('quote', ''))[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
