#!/usr/bin/env python3
"""List the drift of auto-memory pools that a shell can find, one line per finding.

  list-drift.py <config> [<pool>...]   the pools of <config>/projects/*/memory,
                                       or only those named

A finding is a `MEMORY.md` link to a missing file, a memory file no index
links, a file name two pools share, an index past the load limit (only its
first 200 lines or 25KB load at start), a file missing a `When it applies:` or
`When it is wrong:` line, or a lesson never found again: `confirmed` 1 and
`last-confirmed` over STALE_DAYS days old. It ends with the count, so no
output is never mistaken for no drift.
"""
import glob
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import memory  # noqa: E402

STALE_DAYS = 60
INDEX_LINES, INDEX_BYTES = 200, 25_000
LINK = re.compile(r"\]\(([^)]+\.md)\)")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def drift(pools, today):
    found, names = [], defaultdict(list)
    for pool in pools:
        index = os.path.join(pool, "MEMORY.md")
        text = read(index) if os.path.exists(index) else ""
        linked = set(LINK.findall(text))
        found += [f"dangling link: {index} -> {name}" for name in sorted(linked)
                  if not os.path.exists(os.path.join(pool, name))]
        lines, size = len(text.splitlines()), len(text.encode())
        if lines > INDEX_LINES or size > INDEX_BYTES:
            found.append(f"index past its load limit: {index}, {lines} lines, {size} bytes; "
                         f"only the first {INDEX_LINES} lines or {INDEX_BYTES} bytes load")
        for path in sorted(glob.glob(os.path.join(glob.escape(pool), "*.md"))):
            name = os.path.basename(path)
            if name == "MEMORY.md":
                continue
            names[name].append(path)
            if name not in linked:
                found.append(f"unindexed: {path}")
            body = read(path)
            missing = [f for f in ("When it applies:", "When it is wrong:") if f not in body]
            if missing:
                found.append(f"missing {' and '.join(missing)} {path}")
            count, last = memory.fields(path, body)
            if count <= 1 and today - last > timedelta(days=STALE_DAYS):
                found.append(f"never found again: {path}, confirmed {count}, last-confirmed {last.isoformat()}")
    found += [f"one name in {len(paths)} pools: {' '.join(paths)}" for paths in names.values() if len(paths) > 1]
    return found


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    pools = args[1:] or sorted(glob.glob(os.path.join(glob.escape(args[0]), "projects", "*", "memory")))
    missing = [p for p in pools if not os.path.isdir(p)]
    if missing or not pools:
        print(f"could not look: no memory pool at {' '.join(missing) or args[0]}", file=sys.stderr)
        sys.exit(1)
    lines = drift(pools, date.today())
    print("\n".join(lines + [f"drift: {len(lines)} findings in {len(pools)} pools"]))
