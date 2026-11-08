#!/usr/bin/env python3
"""List each file of a skill that sits outside the skill's folder hierarchy.

usage: list-misplaced-references.py [root]

A skill is each `<plugin>/skills/<skill>/` folder of root (default: this repository). It holds `SKILL.md` and the folders
`references/` (playbooks, their split parts and domain folders), `assets/` (texts a script hands over by key or loads
unchanged), `examples/`, `scripts/` and `fixtures/`; any other file or folder in it is misplaced, and a Markdown file under
`scripts/` too, since a playbook there is never routed to. Prints `misplaced <path>: <reason>` lines, then a summary, and exits 1
when it printed any, else 0. Standard library only, Python 3.9."""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOLDERS = ("references", "assets", "examples", "scripts", "fixtures")


def list_files(root):
    git = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True)
    if git.returncode == 0 and git.stdout:
        return sorted(git.stdout.splitlines())
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and ".git" not in path.parts)


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else ROOT).resolve()
    if not root.is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    lines, checked = [], 0
    for path in list_files(root):
        parts = path.split("/")
        if len(parts) < 4 or parts[1] != "skills":
            continue
        checked += 1
        inside = parts[3:]
        if len(inside) == 1 and inside[0] != "SKILL.md":
            lines.append(f"misplaced {path}: a skill's folder holds only SKILL.md and the folders {', '.join(FOLDERS)}")
        elif len(inside) > 1 and inside[0] not in FOLDERS:
            lines.append(f"misplaced {path}: {inside[0]}/ is no folder of a skill; use {', '.join(FOLDERS)}")
        elif len(inside) > 1 and inside[0] == "scripts" and path.endswith(".md"):
            lines.append(f"misplaced {path}: a playbook belongs in references/, a text a script hands over in assets/")
    for line in lines:
        print(line)
    print(f"{checked} skill files, {len(lines)} misplaced")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
