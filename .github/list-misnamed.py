#!/usr/bin/env python3
"""List each plugin file whose name, or an environment variable it reads, breaks the form of its kind.

usage: list-misnamed.py [root]

A plugin is each folder of root (default: this repository) holding `.claude-plugin/plugin.json`. A file name is lowercase words joined by
`-` with its extensions; a Python module under a `lib/` folder may join its words by `_`, a fixed name a tool reads, such as `SKILL.md`, is
capitals, and a command found on PATH, an executable file, has no extension; a file under `examples/` keeps the name of what it imitates.
An environment variable a plugin's code reads is `<PLUGIN>_<WORDS>`, since every plugin's scripts share one environment, unless a tool
outside the plugins sets it, such as Claude Code's `CLAUDE_` names. Prints `misnamed <path>: <reason>` lines, then a summary, and exits 1
when it printed any, else 0. Standard library only, Python 3.9."""

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+)+$")
MODULE_NAME = re.compile(r"^_*[a-z0-9]+(?:_[a-z0-9]+)*_*\.py$")
FIXED_NAME = re.compile(r"^[A-Z]+\.md$")
COMMAND_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENVIRONMENT_READ = re.compile(r"""(?:environ\.get\(\s*|environ\[\s*|getenv\(\s*|process\.env\[\s*)["']([A-Za-z_][A-Za-z0-9_]*)["']|process\.env\.([A-Za-z_][A-Za-z0-9_]*)""")
CODE_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".tsx"}
OUTSIDE_PREFIXES = ("CLAUDE_", "HERDR_", "GH_")  # Claude Code's, herdr's and the GitHub CLI's
OUTSIDE_NAMES = {"PATH", "HOME", "TMPDIR", "USER", "SHELL", "PWD"}


def list_files(root):
    git = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True)
    if git.returncode == 0 and git.stdout:
        return sorted(git.stdout.splitlines())
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and ".git" not in path.parts)


def name_reason(path, parts):
    name = parts[-1]
    if "examples" in parts or FILE_NAME.match(name) or FIXED_NAME.match(name):
        return None
    if MODULE_NAME.match(name) and "lib" in parts[:-1]:
        return None
    if COMMAND_NAME.match(name) and os.access(path, os.X_OK):
        return None
    return "a file name is lowercase words joined by -, with its extension; only a Python module under lib/ joins them by _"


def environment_reasons(path, plugin):
    if path.suffix not in CODE_SUFFIXES and not (not path.suffix and os.access(path, os.X_OK)):
        return []
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return []
    prefix = plugin.upper() + "_"
    names = sorted({first or second for first, second in ENVIRONMENT_READ.findall(text)})
    return [f"reads {name}; a variable a plugin sets is {prefix}<WORDS>" for name in names
            if not name.startswith(prefix) and not name.startswith(OUTSIDE_PREFIXES) and name not in OUTSIDE_NAMES]


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else ROOT).resolve()
    if not root.is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    plugins = {manifest.parent.parent.name for manifest in root.glob("*/.claude-plugin/plugin.json")}
    lines, checked = [], 0
    for relative in list_files(root):
        parts = relative.split("/")
        if parts[0] not in plugins or not (root / relative).is_file():
            continue
        checked += 1
        reason = name_reason(root / relative, parts)
        lines += [f"misnamed {relative}: {reason}"] if reason else []
        lines += [f"misnamed {relative}: {reason}" for reason in environment_reasons(root / relative, parts[0])]
    for line in lines:
        print(line)
    print(f"{checked} files, {len(lines)} misnamed")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
