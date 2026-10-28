#!/usr/bin/env python3
"""List what repeats across dejavu's mapped sessions, one line per repeat, details indented below it.

usage: list-repeats.py <data> [--mistakes <file>]
       list-repeats.py <data> --record <where> <last seen> <key>   record where a repeat went (an issue url, a path or `owner`) in <data>/filed.json

Reads <data>/stats/ and <data>/facets/ for the sessions of the last 14 days and writes <data>/friction.jsonl, every
friction item with an id, for the agent that groups them. A repeat line reads
`<kind> <n> sessions, <r> repos, last <date>[, filed <where>[, seen since]]: <key>`:

- `tool`: a failure signature in 3+ sessions, seen in the last 3 days;
- `instruction`: an owner instruction, case and punctuation aside, in 2+ sessions;
- `mistake`: a group of friction items from --mistakes (`[{"name", "ids"}]`) in 3+ sessions, seen in the last 3 days.

`filed <where>` names where <data>/filed.json records the repeat went; `seen since` means it was sighted after the
record's last sighting, so a closed hand-over needs doing again and an open one does not.
"""
import collections
import glob
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_home  # noqa: E402
import transcript  # noqa: E402

WINDOW_DAYS, ALIVE_DAYS, EXAMPLES = 14, 3, 3
MASK = re.compile(r"<\w+>")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def day(seconds):
    return time.strftime("%Y-%m-%d", time.localtime(seconds))


def memory_lines(key):
    """Lines of memory files that carry the key's longest unmasked phrase, as `file:line: text`."""
    phrase = max(MASK.split(key.split(": ", 1)[-1]), key=len).strip()
    if len(phrase) < 6:
        return []
    found = []
    for path in (path for pool in memory_home.pools() for path in glob.glob(os.path.join(glob.escape(pool), "*.md"))):
        for number, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
            if phrase.lower() in line.lower():
                found.append(f"{path}:{number}: {line.strip()[:160]}")
    return found


def show(kind, key, sightings, filed):
    """Print one repeat; sightings are (time, session path, line, repo)."""
    sessions = {path for _, path, _, _ in sightings}
    repos = sorted({repo for _, _, _, repo in sightings})
    last = int(max(moment for moment, _, _, _ in sightings))
    record = filed.get(key)
    mark = f", filed {record['url']}" + (", seen since" if last > record.get("last_seen", 0) else "") if record else ""
    print(f"{kind} {len(sessions)} sessions, {len(repos)} repos, last {day(last)}{mark}: {key}")
    print(f"  first {day(min(moment for moment, _, _, _ in sightings))}, last seen {last}, repos {', '.join(repos)}")
    seen = set()
    for _, path, line, _ in sorted(sightings, reverse=True):
        if path not in seen and len(seen) < EXAMPLES:
            seen.add(path)
            print(f"  example {path}:{line}")
    for line in memory_lines(key):
        print(f"  memory {line}")


def main(args):
    if len(args) == 5 and args[1] == "--record":
        data, url, last, key = args[0], args[2], float(args[3]), args[4]
        filed = load(os.path.join(data, "filed.json"), {})
        filed[key] = {"url": url, "last_seen": last}
        with open(os.path.join(data, "filed.json"), "w", encoding="utf-8") as out:
            json.dump(filed, out, ensure_ascii=False, indent=1)
        print(f"recorded {url} for: {key}")
        return 0
    if len(args) not in (1, 3) or args[0].startswith("-") or (len(args) == 3 and args[1] != "--mistakes"):
        print(__doc__, file=sys.stderr)
        return 2
    data, now = args[0], time.time()
    filed = load(os.path.join(data, "filed.json"), {})
    stats = {}
    for path in glob.glob(os.path.join(glob.escape(data), "stats", "*.json")):
        row = load(path, None)
        if row and row.get("end") and row["end"] >= now - WINDOW_DAYS * 86400 and transcript.find(row["path"]):
            stats[os.path.basename(path)[:-5]] = row
    alive = now - ALIVE_DAYS * 86400

    tools = collections.defaultdict(list)
    for row in stats.values():
        for failure in row["failures"]:
            tools[failure["key"]].append((failure["time"] or row["end"], row["path"], failure["line"], row["repo"]))
    for key, sightings in sorted(tools.items(), key=lambda item: -len({sighting[1] for sighting in item[1]})):
        if len({sighting[1] for sighting in sightings}) >= 3 and max(sighting[0] for sighting in sightings) >= alive:
            show("tool", key, sightings, filed)

    said, items = collections.defaultdict(list), []
    for session, row in stats.items():
        facet = load(os.path.join(data, "facets", f"{session}.json"), None)
        if not facet:
            continue
        for text in facet.get("instructions") or []:
            normalized = " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())
            if normalized:
                said[normalized].append((row["end"], row["path"], 0, row["repo"]))
        for k, item in enumerate(facet.get("friction") or []):
            items.append(dict(item, id=f"{session[:8]}-{k}", session=session, path=row["path"], time=row["end"], repo=row["repo"]))
    for normalized, sightings in said.items():
        if len({sighting[1] for sighting in sightings}) >= 2:
            show("instruction", normalized, sightings, filed)
    with open(os.path.join(data, "friction.jsonl"), "w", encoding="utf-8") as out:
        out.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in items)

    by_id = {item["id"]: item for item in items}
    for group in load(args[2], []) if len(args) == 3 else []:
        found = [by_id[i] for i in group.get("ids") or [] if i in by_id]
        sightings = [(i["time"], i["path"], i.get("line") or 0, i["repo"]) for i in found]
        if len({sighting[1] for sighting in sightings}) >= 3 and max(sighting[0] for sighting in sightings) >= alive:
            show("mistake", group["name"], sightings, filed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
