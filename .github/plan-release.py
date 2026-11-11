#!/usr/bin/env python3
"""Print the tag to push for each plugin a merge changes, and refuse a merge that changes a plugin without a greater `version` or onto a taken tag.

usage: plan-release.py <base-rev> <merge-rev>

A plugin is each top-level folder of the merge that holds `.claude-plugin/plugin.json`. A plugin with any file changed from
the base to the merge must read a `version` greater than its version at the base, and its tag is `<name>-v<version>`, `name`
from its manifest: no other plugin's tag can equal it, and the older `v<version>` tags, which several plugins share, never
reach it. Prints one tag per line, none when no plugin changed, and exits 0; prints each refusal on stderr and exits 1.
Standard library only, Python 3.9."""

import json
import re
import subprocess
import sys

VERSION = re.compile(r"\d+(?:\.\d+)*")


def git(*argv):
    return subprocess.run(["git", *argv], capture_output=True, text=True)


def manifest(rev, folder):
    """The parsed plugin.json of FOLDER at REV; None when there is none."""
    shown = git("show", f"{rev}:{folder}/.claude-plugin/plugin.json")
    return json.loads(shown.stdout) if shown.returncode == 0 else None


def number(version):
    """VERSION as a tuple of integers; None when it is no dotted number."""
    return tuple(int(part) for part in version.split(".")) if isinstance(version, str) and VERSION.fullmatch(version) else None


def plan(base, merge):
    """The tags to push and the refusals, for the plugins that changed from BASE to MERGE."""
    folders = git("ls-tree", "-d", "--name-only", "--full-tree", merge).stdout.split()
    tags, refusals = [], []
    for folder in folders:
        after = manifest(merge, folder)
        if after is None:
            continue
        changed = git("diff", "--name-only", base, merge, "--", f":(top){folder}").stdout.split()
        if not changed:
            continue
        before = manifest(base, folder)
        version, name = number(after.get("version")), after.get("name")
        if version is None or not name:
            refusals.append(f"{folder}: its manifest holds no dotted `version` and `name`, so it cannot be released")
        elif before and number(before.get("version")) is not None and version <= number(before["version"]):
            refusals.append(f"{folder}: {len(changed)} files changed (first: {changed[0]}) but `version` stays {after['version']}, not above {before['version']}; bump it in the change")
        elif git("rev-parse", "--verify", "--quiet", f"refs/tags/{name}-v{after['version']}").returncode == 0:
            refusals.append(f"{folder}: the tag {name}-v{after['version']} is taken; bump `version` to a free one")
        else:
            tags.append(f"{name}-v{after['version']}")
    return tags, refusals


def main(args):
    if len(args) != 2 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    tags, refusals = plan(*args)
    for refusal in refusals:
        print(refusal, file=sys.stderr)
    if refusals:
        return 1
    for tag in tags:
        print(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
