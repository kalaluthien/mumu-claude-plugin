"""Print what recurs across mapped sessions, with where each went, for the reducers of dejavu and habit."""
import glob
import json
import os
import re
import time

import memory_home

EXAMPLES = 3
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


def facet_items(facet, field):
    """The well-formed items of a facet's list, `line` an integer, since a facet agent may write a stray shape and one bad
    facet must not stop the run."""
    items = []
    for item in facet.get(field) or [] if isinstance(facet, dict) else []:
        if isinstance(item, dict):
            line = str(item.get("line") or 0)
            items.append(dict(item, line=int(line) if line.isascii() and line.isdigit() else 0))
    return items


def show(kind, key, sightings, records, went):
    """Print one repeat; sightings are (time, session path, line, repo), records map a key to where it went, shown after the label `went`."""
    sessions = {path for _, path, _, _ in sightings}
    repos = sorted({repo for _, _, _, repo in sightings})
    last = int(max(moment for moment, _, _, _ in sightings))
    record = records.get(key)
    mark = f", {went} {record['url']}" + (", seen since" if last > record.get("last_seen", 0) else "") if record else ""
    print(f"{kind} {len(sessions)} sessions, {len(repos)} repos, last {day(last)}{mark}: {key}")
    print(f"  first {day(min(moment for moment, _, _, _ in sightings))}, last seen {last}, repos {', '.join(repos)}")
    seen = set()
    for _, path, line, _ in sorted(sightings, reverse=True):
        if path not in seen and len(seen) < EXAMPLES:
            seen.add(path)
            print(f"  example {path}:{line}")
    for line in memory_lines(key):
        print(f"  memory {line}")


def record(path, where, last, key):
    """Record in the JSON file at path that the repeat `key`, last seen at `last`, went to `where`."""
    records = load(path, {})
    records[key] = {"url": where, "last_seen": last}
    with open(path, "w", encoding="utf-8") as out:
        json.dump(records, out, ensure_ascii=False, indent=1)
    print(f"recorded {where} for: {key}")
