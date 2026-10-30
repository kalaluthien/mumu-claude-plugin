#!/usr/bin/env python3
"""Resolve a Schema document's metadata pointers against a repository at one commit.

usage: resolve-pointers.py evidence doc.json --root DIR --sha SHA
      each `meta.evidence` pointer must be `path:line` or `path:line-line` inside that file at SHA; a url or a sha
      counts as unresolved, since only a line can be read back. Prints `evidence: <n> resolved, <k> unresolved`.
usage: resolve-pointers.py constraints doc.json --root DIR --sha SHA
      each `meta.constraint` `<path>#<rule>` must name a bold rule (`**Rule name**`, matched as `rule-name` too) in
      that file at SHA. Prints `constraints: <n> traced, <k> untraced`.

Each failing pointer is printed above the count. Exit status 0 when the count is 1 or more and nothing failed, 1
otherwise, 2 on a usage error.
"""
import json
import re
import subprocess
import sys


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


def main(args):
    modes = {"evidence": evidence, "constraints": constraints}
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
