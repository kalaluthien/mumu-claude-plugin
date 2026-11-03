#!/usr/bin/env python3
"""Measure each Claude Code rules file, so a dream keeps rules lean and scoped to the files they govern.

usage: measure-rules.py <config> [<root>...]   reads <config>/rules/ and each <root>/.claude/rules/, every `*.md` below;
                                               one `rules <file> <n> lines <scoped|always>` line per file, an
                                               `over <file> ...` line per file past the limit, then a count

A file is scoped when its YAML frontmatter, the block between a first line `---` and the next `---`, holds `paths:`;
Claude Code loads it only when a file its globs match is read or edited, and every other rules file at every launch.
"""
import pathlib
import sys

# Claude Code's docs set this target per instruction file: a longer one costs context and lowers adherence
LIMIT = 200


def scoped(lines):
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.startswith("paths:"):
            return True
    return False


def main(args):
    if not args or any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    folders = [pathlib.Path(args[0]) / "rules"] + [pathlib.Path(root) / ".claude" / "rules" for root in args[1:]]
    files = sorted(path for folder in folders if folder.is_dir() for path in folder.rglob("*.md") if path.is_file())
    over = always = 0
    for path in files:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        scope = "scoped" if scoped(lines) else "always"
        print(f"rules {path} {len(lines)} lines {scope}")
        if scope == "always":
            always += len(lines)
        if len(lines) > LIMIT:
            over += 1
            print(f"over {path} {len(lines)} lines of {LIMIT}: split it into files each scoped by `paths:` to the "
                  "files its parts govern, or trim it")
    print(f"{len(files)} rules files, {over} past {LIMIT} lines, {always} lines loaded at every launch: a rule about "
          "certain files belongs in a file scoped to them.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
