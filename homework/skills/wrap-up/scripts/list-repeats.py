#!/usr/bin/env python3
"""List what repeats across dejavu's mapped sessions, one line per repeat, details indented below it.

  list-repeats.py <data> [--mistakes <file>]
  list-repeats.py <data> --record <url> <last seen> <key>   record the issue filed for a repeat in <data>/filed.json

Reads <data>/stats/ and <data>/facets/ for the sessions of the last 14 days and writes <data>/friction.jsonl, every
friction item with an id, for the agent that groups them. A repeat line reads
`<kind> <n> sessions, <r> repos, last <date>[, filed <url>[, seen since]]: <key>`:

- `tool`: a failure signature in 3+ sessions, seen in the last 3 days;
- `instruction`: an owner instruction, case and punctuation aside, in 2+ sessions;
- `mistake`: a group of friction items from --mistakes (`[{"name", "ids"}]`) in 3+ sessions, seen in the last 3 days.

`filed <url>` names the issue <data>/filed.json records for the key; `seen since` means it was sighted after the
record's last sighting, so a closed issue needs filing again and an open one does not.
"""
import collections
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
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
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    found = []
    for path in glob.glob(os.path.join(glob.escape(root), "projects", "*", "memory", "*.md")):
        for number, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
            if phrase.lower() in line.lower():
                found.append(f"{path}:{number}: {line.strip()[:160]}")
    return found


def show(kind, key, sightings, filed):
    """Print one repeat; sightings are (time, session path, line, repo)."""
    sessions = {path for _, path, _, _ in sightings}
    repos = sorted({repo for _, _, _, repo in sightings})
    last = int(max(t for t, _, _, _ in sightings))
    record = filed.get(key)
    mark = f", filed {record['url']}" + (", seen since" if last > record.get("last_seen", 0) else "") if record else ""
    print(f"{kind} {len(sessions)} sessions, {len(repos)} repos, last {day(last)}{mark}: {key}")
    print(f"  first {day(min(t for t, _, _, _ in sightings))}, last seen {last}, repos {', '.join(repos)}")
    seen = set()
    for _, path, line, _ in sorted(sightings, reverse=True):
        if path not in seen and len(seen) < EXAMPLES:
            seen.add(path)
            print(f"  example {path}:{line}")
    for line in memory_lines(key):
        print(f"  memory {line}")


def main():
    if len(sys.argv) == 6 and sys.argv[2] == "--record":
        data, url, last, key = sys.argv[1], sys.argv[3], float(sys.argv[4]), sys.argv[5]
        filed = load(os.path.join(data, "filed.json"), {})
        filed[key] = {"url": url, "last_seen": last}
        with open(os.path.join(data, "filed.json"), "w", encoding="utf-8") as out:
            json.dump(filed, out, ensure_ascii=False, indent=1)
        print(f"recorded {url} for: {key}")
        return
    if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != "--mistakes"):
        sys.exit(__doc__)
    data, now = sys.argv[1], time.time()
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
    for key, sightings in sorted(tools.items(), key=lambda kv: -len({s[1] for s in kv[1]})):
        if len({s[1] for s in sightings}) >= 3 and max(s[0] for s in sightings) >= alive:
            show("tool", key, sightings, filed)

    said, items = collections.defaultdict(list), []
    for sid, row in stats.items():
        facet = load(os.path.join(data, "facets", f"{sid}.json"), None)
        if not facet:
            continue
        for text in facet.get("instructions") or []:
            norm = " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())
            if norm:
                said[norm].append((row["end"], row["path"], 0, row["repo"]))
        for k, item in enumerate(facet.get("friction") or []):
            items.append(dict(item, id=f"{sid[:8]}-{k}", session=sid, path=row["path"], time=row["end"], repo=row["repo"]))
    for norm, sightings in said.items():
        if len({s[1] for s in sightings}) >= 2:
            show("instruction", norm, sightings, filed)
    with open(os.path.join(data, "friction.jsonl"), "w", encoding="utf-8") as out:
        out.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in items)

    by_id = {item["id"]: item for item in items}
    for group in load(sys.argv[3], []) if len(sys.argv) == 4 else []:
        found = [by_id[i] for i in group.get("ids") or [] if i in by_id]
        sightings = [(i["time"], i["path"], i.get("line") or 0, i["repo"]) for i in found]
        if len({s[1] for s in sightings}) >= 3 and max(s[0] for s in sightings) >= alive:
            show("mistake", group["name"], sightings, filed)


if __name__ == "__main__":
    main()
