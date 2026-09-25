#!/usr/bin/env python3
"""Print mumu-document's four measures at a git ref: files, lines, concepts, instructions.

usage: measure-document.py <ref> [<ref> ...]; one row per ref, read with git, never the working tree.

- files: `git ls-files mumu-document` at the ref.
- lines: their newline count, as `wc -l` totals it.
- concepts: widget files + skin tokens (each `--name:` defined in skin.css) + table rows
  (header and divider excluded) and numbered list items in the text: SKILL.md, every
  reference `.md` and each widget's spec comment.
- instructions: lines of that text containing must, never, always, only or do not, or
  starting (after a list marker, table pipe or bold) with a verb from VERBS.
"""
import re
import subprocess
import sys

ROOT = "mumu-document"
VERBS = frozenset("""add ask attach avoid check choose copy cut delete do don't draw drop export fill fix
follow give hand keep link load make mark name open pair pass pick place prefer publish put read
render reference reread reserve run say send set show start take use write""".split())
RULE = re.compile(r"\b(must|never|always|only|do not)\b", re.I)
FIRST = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+|\|\s*)?(?:\*\*)?([A-Za-z']+)")
NUMBERED = re.compile(r"^\s*\d+\.\s")
DIVIDER = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def text_lines(path, body):
    """The lines of a file that count as text: a .md file whole, a widget its spec comment."""
    if path.endswith(".md") and "/skills/" in path:
        return body.splitlines()
    if "/widgets/" in path and path.endswith(".html"):
        spec = re.match(r"<!--(.*?)-->", body, re.S)
        return spec.group(1).splitlines() if spec else []
    return []


def measure(ref):
    paths = git("ls-tree", "-r", "--name-only", ref, "--", ROOT).split()
    lines = concepts = instructions = 0
    for path in paths:
        body = git("show", f"{ref}:{path}")
        lines += body.count("\n")
        if "/widgets/" in path and path.endswith(".html"):
            concepts += 1
        if path.endswith("skin.css"):
            concepts += len(set(re.findall(r"(--[\w-]+)\s*:", body)))
        table, header = False, True
        for line in text_lines(path, body):
            if line.lstrip().startswith("|"):
                header = not table
                table = True
                concepts += not header and not DIVIDER.match(line)
            else:
                table = False
            concepts += bool(NUMBERED.match(line))
            first = FIRST.match(line)
            instructions += bool(RULE.search(line) or first and first.group(1).lower() in VERBS)
    return {"files": len(paths), "lines": lines, "concepts": concepts, "instructions": instructions}


def main():
    if len(sys.argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    print("ref\tfiles\tlines\tconcepts\tinstructions")
    for ref in sys.argv[1:]:
        print("\t".join([ref] + [str(v) for v in measure(ref).values()]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
