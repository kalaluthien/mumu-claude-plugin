#!/usr/bin/env python3
"""List each plugin whose files at HEAD no release tag covers.

usage: list-unreleased.py [root]

A plugin is each top-level folder of root (default: this repository) that holds `.claude-plugin/plugin.json`. A merge releases
the plugins it changes by the tag `<name>-v<version>`, so a plugin is released when that tag exists and its folder at the tag
equals its folder at HEAD, and waits for its release when no tag names its version and that version is greater than every
`<name>-v*` tag's. Any other plugin holds a change no release covers. A shallow clone, or one that holds no release tag,
lists every plugin, since the tags it lacks are what a release is read from; a root with no git history lists no plugin.
Prints `unreleased <folder>: <detail>` lines, then `<n> plugins, <n> unreleased`, and exits 1 when it printed any
`unreleased` line, else 0. Standard library only, Python 3.9."""

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = re.compile(r"\d+(?:\.\d+)*")


def git(root, *argv):
    return subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True)


def number(version):
    """VERSION as a tuple of integers; None when it is no dotted number."""
    return tuple(int(part) for part in version.split(".")) if isinstance(version, str) and VERSION.fullmatch(version) else None


def unreleased(root, folder):
    """Why FOLDER at HEAD holds a change no release covers; None when a tag covers it or its version waits for the next one."""
    shown = git(root, "show", f"HEAD:{folder}/.claude-plugin/plugin.json")
    try:
        manifest = json.loads(shown.stdout)
    except ValueError:
        return "its manifest is no JSON"
    if not isinstance(manifest, dict):
        return "its manifest is no JSON object"
    name, version = manifest.get("name"), manifest.get("version")
    if not name or number(version) is None:
        return "its manifest holds no `name` and dotted `version`"
    tag = f"{name}-v{version}"
    if git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}").returncode == 0:
        compared = git(root, "diff", "--name-only", tag, "HEAD", "--", folder)
        if compared.returncode:
            return f"{tag} cannot be compared with HEAD, as in a shallow clone; fetch the whole history"
        changed = compared.stdout.split()
        return changed and f"{len(changed)} files changed since {tag}, first {changed[0]}; bump `version` in the change that touches it"
    released = [found for line in git(root, "tag", "-l", f"{name}-v*").stdout.split() if (found := number(line[len(name) + 2:]))]
    highest = max(released, default=None)
    return highest and number(version) <= highest and f"`version` {version} has no tag and is not above the released {'.'.join(map(str, highest))}; bump it above"


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0]).resolve() if args else ROOT
    folders = []
    if git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode == 0:
        folders = [folder for folder in git(root, "ls-tree", "-d", "--name-only", "HEAD").stdout.split()
                   if git(root, "cat-file", "-e", f"HEAD:{folder}/.claude-plugin/plugin.json").returncode == 0]
    shallow = git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    blind = "this clone is shallow" if shallow else folders and not git(root, "tag", "-l", "*-v*").stdout.split() and "this clone holds no release tag"
    lines = ([f"unreleased {folder}: {blind}, so its release cannot be read; fetch the whole history and its tags" for folder in folders] if blind
             else [f"unreleased {folder}: {why}" for folder in folders if (why := unreleased(root, folder))])
    for line in lines:
        print(line)
    print(f"{len(folders)} plugins, {len(lines)} unreleased")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
