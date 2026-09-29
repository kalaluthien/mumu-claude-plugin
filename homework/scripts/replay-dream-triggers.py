#!/usr/bin/env python3
"""Replay candidate dream triggers over past session transcripts.

  replay-dream-triggers.py [<projects dir>]   default ~/.claude/projects

Every top-level `*/<session>.jsonl` gives its memory events: a Write, Edit or
Bash call naming `<pool>/memory/<file>.md` of a pool that exists. A later
session's shrinking Edit, `rm`, `mv`, `sed -i` or Python rewrite of that file
is a fix, as dream's own fixes and ad hoc cleanups are; its item is pending
from the last write by another session (else from START) until the fix.

The stops of interactive sessions (no `sdk` entrypoint, as takeaway.py skips),
merged in time order from START, are where a trigger may ask. A trigger asks
at a stop once its condition holds since its last ask, then counts afresh; an
ask finds a fix when an item pending then was born after the previous ask, or
a shell defect of dream step 1 in today's pools was born since. Per trigger
it prints its asks, how many found a fix, and the fixes pending at an ask.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

START = datetime(2026, 9, 12, tzinfo=timezone.utc).timestamp()
DAY = 86400
PATH = re.compile(r"(-[A-Za-z0-9_.-]+)/memory/([\w.-]+\.md)")
REMOVE = re.compile(r"\b(rm|mv|trash)\b")
REWRITE = re.compile(r"sed -i|write_text|open\([^)]*['\"]w|\.replace\(")
CREATE = re.compile(r">\|?|\btee\b")


def entries_of(path):
    out = []
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def seconds(entry):
    try:
        return datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def calls(entry):
    body = (entry.get("message") or {}).get("content") if entry.get("type") == "assistant" else None
    return [b for b in body or [] if isinstance(b, dict) and b.get("type") == "tool_use"]


def memory_events(root, entries, session):
    """(time, session, pool, file, op, text): op is write, fix or index."""
    for entry in entries:
        at = seconds(entry)
        for call in calls(entry) if at else []:
            args, name = call.get("input") or {}, call.get("name")
            if name in ("Write", "Edit"):
                found = PATH.search(str(args.get("file_path", "")))
                if not found or not os.path.isdir(os.path.join(root, found[1])):
                    continue
                text = args.get("content") or args.get("new_string") or ""
                shrink = name == "Edit" and len(text) < len(args.get("old_string") or "")
                op = "index" if found[2] == "MEMORY.md" else "fix" if shrink else "write"
                yield at, session, found[1], found[2], op, text
            elif name == "Bash":
                command = str(args.get("command", ""))
                for pool, file in set(PATH.findall(command)):
                    if not os.path.isdir(os.path.join(root, pool)):
                        continue
                    if file == "MEMORY.md":
                        yield at, session, pool, file, "index", command
                    elif REMOVE.search(command) or REWRITE.search(command):
                        yield at, session, pool, file, "fix", command
                    elif CREATE.search(command):
                        yield at, session, pool, file, "write", command


def items_of(events):
    """(born, fixed) per fix: pending from the last write by another session."""
    items, last = [], {}
    for at, session, pool, file, op, _ in events:
        key = (pool, file)
        if op == "fix":
            born = max([t for t, s in last.get(key, []) if s != session], default=None)
            if born is not None or not last.get(key):
                items.append((born or START, at))
        if op in ("write", "fix"):
            last.setdefault(key, []).append((at, session))
    return items


def defects(root, events):
    """Birth times of dream step 1's shell defects in today's pools: dangling
    links, unindexed files, duplicate names; transcripts cannot rebuild an
    index, so a defect since fixed is not seen."""
    born = {}
    for at, _, pool, file, op, _ in events:
        born.setdefault((pool, file), at)
    out, names = [], {}
    for pool in glob.glob(os.path.join(root, "*", "memory")):
        key = os.path.basename(os.path.dirname(pool))
        try:
            with open(os.path.join(pool, "MEMORY.md"), encoding="utf-8") as handle:
                index = handle.read()
        except OSError:
            index = ""
        for link in re.findall(r"\(([^)]*\.md)\)", index):
            if not os.path.exists(os.path.join(pool, link)):
                out.append(born.get((key, "MEMORY.md"), START))
        for path in glob.glob(os.path.join(pool, "*.md")):
            file = os.path.basename(path)
            if file != "MEMORY.md":
                names.setdefault(file, []).append(born.get((key, file), START))
                if f"({file})" not in index:
                    out.append(born.get((key, file), START))
    out += [sorted(times)[1] for times in names.values() if len(times) > 1]
    return out


def replay(stops, events, items, shell, fires):
    """Asks, asks that found a fix, and fixes reached, for a trigger
    fires(last ask, now, files written since, shell defects born since)."""
    asks = found = 0
    reached, last = set(), START
    for now in stops:
        written = {(p, f) for at, _, p, f, op, _ in events if last < at <= now and op in ("write", "fix")}
        new = [born for born in shell if last < born <= now]
        if not fires(last, now, written, new):
            continue
        pending = [i for i, (born, fixed) in enumerate(items) if last < born <= now < fixed]
        asks, found, last = asks + 1, found + bool(pending or new), now
        reached.update(pending)
    return asks, found, len(reached)


TRIGGERS = [
    ("memory files written >= 3", lambda last, now, written, new: len(written) >= 3),
    ("memory files written >= 5", lambda last, now, written, new: len(written) >= 5),
    ("memory files written >= 10", lambda last, now, written, new: len(written) >= 10),
    ("shell defects >= 1", lambda last, now, written, new: bool(new)),
    ("days since last >= 3", lambda last, now, written, new: now - last >= 3 * DAY),
    ("days since last >= 7", lambda last, now, written, new: now - last >= 7 * DAY),
]


def main(root):
    events, stops = [], []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.jsonl"))):
        entries = entries_of(path)
        events += memory_events(root, entries, os.path.basename(path))
        if any(str(e.get("entrypoint", "")).startswith("sdk") for e in entries):
            continue
        stops += [seconds(e) for e in entries if e.get("subtype") == "stop_hook_summary" and (seconds(e) or 0) >= START]
    events.sort(key=lambda e: e[0])
    stops.sort()
    items = [(born, fixed) for born, fixed in items_of(events) if fixed >= START]
    shell = defects(root, events)
    print(f"stops: {len(stops)} since 2026-09-12; memory events: {len(events)}; "
          f"fixes: {len(items)}; shell defects today: {len(shell)}\n")
    print("| trigger | asks | found a fix | fixes reached |")
    print("| --- | --- | --- | --- |")
    for label, fires in TRIGGERS:
        asks, found, reached = replay(stops, events, items, shell, fires)
        print(f"| {label} | {asks} | {found} | {reached} |")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/projects")))
