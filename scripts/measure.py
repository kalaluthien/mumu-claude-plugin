#!/usr/bin/env python3
"""Print a plugin's size: files, words, sentences, features, evals, concepts, steps.

Usage: measure.py <plugin-dir> [<plugin-dir> ...]; one row per directory.

- files: every file under the directory.
- words: words of the prose the sentences are counted in, so a count that
  falls by joining sentences shows here as words that did not.
- sentences: in Markdown outside code fences, and in script comments and
  docstrings, each `.`, `;`, `?` or `!` that ends a word; a list item or table
  row with none counts as one.
- features: harness features used: skills, agents, hook registrations, `bin/`
  executables.
- evals: eval cases.
- concepts: distinct backticked spans in Markdown, each read as its first word
  and up to two lowercase words after it, so a command counts at subcommand
  depth; a span opening with a flag or punctuation is no name.
- steps: numbered list items and numbered headings in Markdown.
"""
import json
import pathlib
import re
import sys

END = re.compile(r"[.;?!](?=\s|$)")
ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s|^\s*\|")
STEP = re.compile(r"^\s*\d+\.\s|^#+\s*\d+\.")
SPAN = re.compile(r"`([^`]*)`")
NAME = re.compile(r"\s*([A-Za-z$][\w$.:{}/-]*?)[:,]?((?: [a-z][a-z-]*){0,2})(?=\s|$)")


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
    words = sentences = steps = 0
    concepts = set()
    for path in files:
        if path.suffix == ".json":
            continue
        for line in prose(path):
            ends = len(END.findall(line))
            words += len(line.split())
            sentences += ends or (1 if ITEM.match(line) else 0)
            if path.suffix == ".md":
                steps += bool(STEP.match(line))
                names = (NAME.match(span) for span in SPAN.findall(line))
                concepts.update("".join(n.groups()) for n in names if n)
    hooks = root / "hooks" / "hooks.json"
    registrations = sum(len(v) for v in json.loads(hooks.read_text())["hooks"].values()) if hooks.exists() else 0
    features = (len(list(root.glob("skills/*/SKILL.md"))) + len(list(root.glob("agents/*.md")))
                + registrations + len(list(root.glob("bin/*"))))
    return {"files": len(files), "words": words, "sentences": sentences, "features": features,
            "evals": len(list(root.glob("evals/*/prompt.md"))), "concepts": len(concepts), "steps": steps}


print("dir\tfiles\twords\tsentences\tfeatures\tevals\tconcepts\tsteps")
for arg in sys.argv[1:]:
    row = measure(pathlib.Path(arg))
    print("\t".join([arg] + [str(v) for v in row.values()]))
