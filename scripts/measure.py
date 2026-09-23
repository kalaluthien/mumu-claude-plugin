#!/usr/bin/env python3
"""Print a plugin's size as five counts: files, sentences, features, concepts, steps.

Usage: measure.py <plugin-dir> [<plugin-dir> ...]; one row per directory.

- files: every file under the directory.
- sentences: in Markdown outside code fences, and in script comments and
  docstrings, each `.`, `?` or `!` that ends a word; a list item or table row
  with none counts as one.
- features: harness features used: skills, agents, hook registrations,
  `bin/` executables, eval cases.
- concepts: distinct first words of backticked spans in Markdown, the names a
  reader must recognise: a command counts as its program.
- steps: numbered list items and numbered headings in Markdown.
"""
import json
import pathlib
import re
import sys

END = re.compile(r"[.?!](?=\s|$)")
ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s|^\s*\|")
STEP = re.compile(r"^\s*\d+\.\s|^#+\s*\d+\.")
SPAN = re.compile(r"`\s*([^`\s]+)[^`]*`")


def prose(path):
    lines, fenced, doc = [], False, False
    for line in path.read_text(errors="replace").splitlines():
        if path.suffix == ".md":
            if line.lstrip().startswith("```"):
                fenced = not fenced
            elif not fenced and not re.match(r"^\s*\|?\s*:?-{3}", line):
                lines.append(line)
            continue
        if line.count('"""') % 2:
            doc = not doc
            lines.append(line.replace('"""', ""))
        elif doc or line.lstrip().startswith("#") and not line.startswith("#!"):
            lines.append(line.lstrip("# "))
    return lines


def measure(root):
    files = [p for p in root.rglob("*") if p.is_file()]
    sentences = steps = 0
    concepts = set()
    for path in files:
        if path.suffix == ".json":
            continue
        for line in prose(path):
            ends = len(END.findall(line))
            sentences += ends or (1 if ITEM.match(line) else 0)
            if path.suffix == ".md":
                steps += bool(STEP.match(line))
                concepts.update(SPAN.findall(line))
    hooks = root / "hooks" / "hooks.json"
    registrations = sum(len(v) for v in json.loads(hooks.read_text())["hooks"].values()) if hooks.exists() else 0
    features = (len(list(root.glob("skills/*/SKILL.md"))) + len(list(root.glob("agents/*.md")))
                + registrations + len(list(root.glob("bin/*"))) + len(list(root.glob("evals/*/prompt.md"))))
    return {"files": len(files), "sentences": sentences, "features": features,
            "concepts": len(concepts), "steps": steps}


print("dir\tfiles\tsentences\tfeatures\tconcepts\tsteps")
for arg in sys.argv[1:]:
    row = measure(pathlib.Path(arg))
    print("\t".join([arg] + [str(v) for v in row.values()]))
