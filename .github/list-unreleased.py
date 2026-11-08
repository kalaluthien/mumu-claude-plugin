#!/usr/bin/env python3
"""List each plugin whose files changed after the commit that last set its `version`.

usage: list-unreleased.py [root]

A plugin is each top-level folder of root (default: this repository) that holds `.claude-plugin/plugin.json`. A merge releases
the plugins it changes, so a plugin whose folder differs at HEAD from the commit that last changed its manifest's `version`
holds a change no release covers. Needs the whole history, so a shallow clone lists every plugin as unreleased.
Prints `unreleased <folder>: <detail>` lines, then `<n> plugins, <n> unreleased`, and exits 1 when it printed any
`unreleased` line, else 0. Standard library only, Python 3.9."""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(root, *argv):
    return subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True)


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0]).resolve() if args else ROOT
    if git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode:
        print(__doc__, file=sys.stderr)
        return 2
    folders = [folder for folder in git(root, "ls-tree", "-d", "--name-only", "HEAD").stdout.split()
               if git(root, "cat-file", "-e", f"HEAD:{folder}/.claude-plugin/plugin.json").returncode == 0]
    unreleased = []
    shallow = git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    for folder in folders:
        if shallow:
            unreleased.append(f"unreleased {folder}: this clone is shallow, so the commit that set its version is unknown; fetch the whole history")
            continue
        manifest = f"{folder}/.claude-plugin/plugin.json"
        released = git(root, "log", "-1", "--format=%H", "-G", '"version":', "HEAD", "--", manifest).stdout.strip()
        if not released:
            unreleased.append(f"unreleased {folder}: no commit in this history sets its version")
            continue
        changed = git(root, "diff", "--name-only", released, "HEAD", "--", folder).stdout.split()
        if changed:
            unreleased.append(f"unreleased {folder}: {len(changed)} files changed since {released[:8]} set its version, first {changed[0]}; bump `version` in the change that touches it")
    for line in unreleased:
        print(line)
    print(f"{len(folders)} plugins, {len(unreleased)} unreleased")
    return 1 if unreleased else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
