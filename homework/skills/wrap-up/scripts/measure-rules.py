#!/usr/bin/env python3
"""Measure each Claude Code rules file and the set every session loads, so a dream keeps rules lean and scoped to the files they govern.

usage: measure-rules.py <config> [<root>...]   reads <config>/rules/ and each <root>/.claude/rules/, every `*.md` below;
                                               one `rules <file> <n> lines <scoped|always>` line per file, an
                                               `over <file> ...` line per file past the limit, a count, then an
                                               `always-loaded ...` total, with `over budget ...` before it past BUDGET

A file is scoped when its YAML frontmatter, the block between a first line `---` and the next `---`, holds `paths:`;
Claude Code loads it only when a file its globs match is read or edited, and every other rules file at every launch.
The set every session loads is <config>/CLAUDE.md, each unscoped rules file of <config>/rules/ and the memory home's
index, of which only the first 200 lines or 25,000 bytes load.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_home  # noqa: E402

# Claude Code's docs set this target per instruction file: a longer one costs context and lowers adherence
LIMIT = 200
# about 6,000 tokens: dotclaude #297 measured a 7,574-byte CLAUDE.md as 2,277 first-turn tokens, 3.3 bytes each
BUDGET = 20_000
INDEX_LINES, INDEX_BYTES = 200, 25_000


def loaded_bytes(path, lines=None, limit=None):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    if lines:
        text = "".join(text.splitlines(keepends=True)[:lines])
    size = len(text.encode())
    return min(size, limit) if limit else size


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
    config = pathlib.Path(args[0])
    folders = [config / "rules"] + [pathlib.Path(root) / ".claude" / "rules" for root in args[1:]]
    files = sorted(path for folder in folders if folder.is_dir() for path in folder.rglob("*.md") if path.is_file())
    over = always = 0
    user_bytes = loaded_bytes(config / "CLAUDE.md")
    for path in files:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        scope = "scoped" if scoped(lines) else "always"
        print(f"rules {path} {len(lines)} lines {scope}")
        if scope == "always":
            always += len(lines)
            if path.is_relative_to(config / "rules"):
                user_bytes += loaded_bytes(path)
        if len(lines) > LIMIT:
            over += 1
            print(f"over {path} {len(lines)} lines of {LIMIT}: split it into files each scoped by `paths:` to the "
                  "files its parts govern, or trim it")
    print(f"{len(files)} rules files, {over} past {LIMIT} lines, {always} lines loaded at every launch: a rule about "
          "certain files belongs in a file scoped to them.")
    home = memory_home.home(None, config)
    if home:
        user_bytes += loaded_bytes(home / "MEMORY.md", INDEX_LINES, INDEX_BYTES)
    if user_bytes > BUDGET:
        print(f"over budget: every session loads {user_bytes} bytes of {BUDGET}: move a narrow rule or index line "
              "into a memory file, or scope it by `paths:`")
    print(f"always-loaded {user_bytes} bytes of a {BUDGET}-byte budget, about {user_bytes * 10 // 33} tokens: "
          f"{config / 'CLAUDE.md'}, its unscoped rules files and the memory home's index")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
