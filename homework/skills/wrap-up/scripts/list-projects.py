#!/usr/bin/env python3
"""List each project root that still exists, read from the `cwd` its interactive transcripts record, so a dream reads every project.

usage: list-projects.py <config>   reads <config>/projects/*/*.jsonl; one `project <root>` line per root, a worktree
                                   folded into its main checkout, then a count

A project key is never turned back into a path, since `-` stands for every character that is not a letter or a digit;
the `cwd` a transcript records is the path itself. A session run by `claude -p` or the SDK (`entrypoint` `sdk-*`)
works in folders it made for one run, and a folder under the system's temporary folders lasts one run too, so neither is
a project.
"""
import glob
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_home  # noqa: E402

# a transcript records its cwd on its first entries; reading on wastes time on long sessions
SCAN_LINES = 50
TEMPORARY = {os.path.realpath(path) for path in (tempfile.gettempdir(), "/tmp", "/var/folders")}


def cwd_of(path):
    """The first `cwd` an interactive transcript records, None for an SDK session or when its first lines hold none."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for _, line in zip(range(SCAN_LINES), handle):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("entrypoint", "")).startswith("sdk"):
                    return None
                if isinstance(entry.get("cwd"), str) and entry["cwd"]:
                    return entry["cwd"]
    except OSError:
        return None
    return None


def temporary(root):
    real = os.path.realpath(root)
    return any(real == top or real.startswith(top + os.sep) for top in TEMPORARY)


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    config = pathlib.Path(args[0])
    seen = set()
    for folder in sorted(glob.glob(os.path.join(glob.escape(str(config)), "projects", "*"))):
        for path in glob.glob(os.path.join(glob.escape(folder), "*.jsonl")):
            cwd = cwd_of(path)
            if cwd:
                seen.add(cwd)
    roots = sorted({str(memory_home.checkout(cwd)) for cwd in seen if os.path.isdir(cwd)})
    roots = [root for root in roots if not temporary(root)]
    for root in roots:
        print(f"project {root}")
    print(f"{len(roots)} project roots exist of {len(seen)} working folders the interactive transcripts record: a dream reads each "
          "root's instruction files, documents and skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
