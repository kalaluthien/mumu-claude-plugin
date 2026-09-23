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
  and its subcommands: the lowercase words after it, past any option and its
  `<placeholder>` value, two deep for `gh` and `herdr`, whose commands are
  noun then verb, and one deep otherwise; a span opening with a flag or
  punctuation is no name.
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
NAME = re.compile(r"[A-Za-z$/][\w$.:{}/-]*")
WORD = re.compile(r"[a-z][a-z-]*")
DEPTH = {"gh": 2, "herdr": 2}


def concept(span):
    words = span.split()
    if not words or not NAME.fullmatch(words[0].rstrip(":,")):
        return None
    name = words[0].rstrip(":,")
    if words[0] != name:
        return name
    parts, rest = [name], words[1:]
    while rest and len(parts) <= DEPTH.get(name, 1):
        if rest[0].startswith("-"):
            rest = rest[2:] if len(rest) > 1 and rest[1].startswith("<") else rest[1:]
        elif WORD.fullmatch(rest[0]):
            parts.append(rest[0])
            rest = rest[1:]
        else:
            break
    return " ".join(parts)


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
                concepts.update(filter(None, map(concept, SPAN.findall(line))))
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
