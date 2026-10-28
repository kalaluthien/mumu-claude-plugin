#!/usr/bin/env python3
"""Resolve a Schema document's metadata pointers against a repository at one commit.

usage: resolve-pointers.py evidence doc.json --root DIR --sha SHA
      each `meta.evidence` pointer must be `path:line` or `path:line-line` inside that file at SHA; a url or a sha
      counts as unresolved, since only a line can be read back. Prints `evidence: <n> resolved, <k> unresolved`.
usage: resolve-pointers.py constraints doc.json --root DIR --sha SHA
      each `meta.constraint` `<path>#<rule>` must name a bold rule (`**Rule name**`, matched as `rule-name` too) in
      that file at SHA. Prints `constraints: <n> traced, <k> untraced`.
usage: resolve-pointers.py faults doc.json --root DIR --sha SHA
      each `meta.note` written `<Word>: <text>` is a fault; it is named when <Word> is Missing, Illegal, Redundant or
      Overloaded and its element's evidence all resolves. Prints `faults: <n> named, <k> unresolved`.
usage: resolve-pointers.py drift doc.json --root DIR --sha SHA [--to NEW]
      each `meta.evidence` `path:line` pointer read at SHA is `changed` when a commit up to NEW (HEAD by default)
      touched one of its lines, or `gone` when its file is not at NEW; a line that only moved stays unchanged. Prints
      `drift: <n> unchanged, <k> changed`, `gone` counted as changed; a url or a sha is skipped, and a `path:line`
      that does not resolve at SHA is printed `unresolved` and fails the run, since a wrong SHA or root reads as no
      drift.

Each failing pointer is printed above the count. Exit status 0 when the count is 1 or more and nothing failed, 1
otherwise, 2 on a usage error.
"""
import json
import re
import subprocess
import sys

FAULTS = ("Missing", "Illegal", "Redundant", "Overloaded")


def find_metadata(value, path="$"):
    """(path, meta) for every element of the document that carries metadata."""
    if isinstance(value, dict):
        if isinstance(value.get("meta"), dict):
            yield path, value["meta"]
        for key, child in value.items():
            yield from find_metadata(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from find_metadata(child, f"{path}[{index}]")


class Repository:
    def __init__(self, root, sha):
        self.root, self.sha, self.cache = root, sha, {}

    def text(self, path):
        if path not in self.cache:
            got = subprocess.run(["git", "-C", self.root, "show", f"{self.sha}:{path}"], capture_output=True, text=True)
            self.cache[path] = got.stdout if got.returncode == 0 else None
        return self.cache[path]

    def line(self, pointer):
        """Why a `path:line` pointer does not resolve, or None when it does."""
        matched = re.fullmatch(r"([^\s:#]+):([0-9]+)(?:-([0-9]+))?", pointer)
        if not matched:
            return "not a path:line"
        text = self.text(matched[1])
        if text is None:
            return f"no {matched[1]} at {self.sha}"
        last, line_count = int(matched[3] or matched[2]), len(text.splitlines())
        return None if 1 <= int(matched[2]) <= last <= line_count else f"{matched[1]} has {line_count} lines"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def evidence(document, repository):
    # the document's own evidence is the commit it was read at, not a pointer
    metadata_items = [metadata for where, metadata in find_metadata(document) if where != "$"]
    bad = [f"unresolved {pointer}: {why}" for metadata in metadata_items for pointer in metadata.get("evidence", []) if (why := repository.line(pointer))]
    good = sum(len(metadata.get("evidence", [])) for metadata in metadata_items) - len(bad)
    return bad, f"evidence: {good} resolved, {len(bad)} unresolved", good


def constraints(document, repository):
    bad, good = [], 0
    for _, metadata in find_metadata(document):
        for constraint in metadata.get("constraint", []):
            path, _, rule = constraint.partition("#")
            text = repository.text(path)
            names = {slug(bold) for bold in re.findall(r"\*\*([^*]+)\*\*", text or "")}
            if slug(rule) in names:
                good += 1
            else:
                bad.append(f"untraced {constraint}: " + (f"no {path} at {repository.sha}" if text is None else f"no bold rule {rule} in {path}"))
    return bad, f"constraints: {good} traced, {len(bad)} untraced", good


def faults(document, repository):
    bad, good = [], 0
    for where, metadata in find_metadata(document):
        word = re.match(r"([A-Z][a-z]+): ", metadata.get("note", ""))
        if not word:
            continue
        if word[1] not in FAULTS:
            bad.append(f"unresolved {where}: {word[1]} is none of {', '.join(FAULTS)}")
        elif not metadata.get("evidence"):
            bad.append(f"unresolved {where}: a {word[1]} fault with no evidence")
        elif why := next((f"{pointer}: {reason}" for pointer in metadata["evidence"] if (reason := repository.line(pointer))), None):
            bad.append(f"unresolved {where}: {why}")
        else:
            good += 1
    return bad, f"faults: {good} named, {len(bad)} unresolved", good


def touched(root, sha, to, path):
    """The lines of `path` at `sha` that the diff to `to` removes or replaces, or None when `path` is gone at `to`."""
    if subprocess.run(["git", "-C", root, "cat-file", "-e", f"{to}:{path}"], capture_output=True).returncode:
        return None
    diff = subprocess.run(["git", "-C", root, "diff", "-U0", sha, to, "--", path], capture_output=True, text=True).stdout
    lines = set()
    for start, count in re.findall(r"^@@ -([0-9]+)(?:,([0-9]+))? ", diff, re.M):
        length = 1 if count == "" else int(count)
        # a pure insertion (count 0) lands between two lines, so it touches the one above it
        lines |= set(range(int(start), int(start) + length)) if length else {int(start)}
    return lines


def drift(document, repository, to):
    bad, unresolved, good = [], [], 0
    for _, metadata in find_metadata(document):
        for pointer in metadata.get("evidence", []):
            if why := repository.line(pointer):
                if why != "not a path:line":
                    unresolved.append(f"unresolved {pointer}: {why}")
                continue
            path, first_line, last_line = re.fullmatch(r"([^\s:#]+):([0-9]+)(?:-([0-9]+))?", pointer).groups()
            hit = touched(repository.root, repository.sha, to, path)
            if hit is None:
                bad.append(f"{pointer}: gone at {to}")
            elif hit & set(range(int(first_line), int(last_line or first_line) + 1)):
                bad.append(f"{pointer}: changed by {to}")
            else:
                good += 1
    return unresolved + bad, f"drift: {good} unchanged, {len(bad)} changed", good


def main(args):
    modes = {"evidence": evidence, "constraints": constraints, "faults": faults}
    if len(args) == 8 and args[0] == "drift" and args[6] == "--to":
        to, args = args[7], args[:6]
    elif len(args) == 6 and args[0] == "drift":
        to = "HEAD"
    if args[:1] == ["drift"]:
        modes["drift"] = lambda document, repository: drift(document, repository, to)
    if len(args) != 6 or args[0] not in modes or args[2] != "--root" or args[4] != "--sha":
        print(__doc__, file=sys.stderr)
        return 2
    try:
        document = json.load(open(args[1], encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"{args[1]}: {e}", file=sys.stderr)
        return 2
    bad, count, good = modes[args[0]](document, Repository(args[3], args[5]))
    print("\n".join(bad + [count]))
    return 0 if good and not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
