#!/usr/bin/env python3
"""Migrate a document in paperwork's old system.json shape to the Schema (assets/schema.json, version 1).

usage: migrate-schema.py old.json|-                     print the Schema document
       migrate-schema.py --audit old.json|- new.json    compare a migrated document with its source, leaf by leaf:
                                                        print each rename and addition, any other difference as
                                                        `changed:`, then `facts: <n> old leaf values, <k> lost`

The migration renames the kind `schema` to `topology`, adds `version`, marks each node that opens a level of another
kind `link: view`, and marks `link: nest` on each same-kind open whose ports do not carry every edge of its node.
Exit status 0 means nothing lost or changed, 1 a loss or change, 2 a usage error.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5] / "lib"))

from schema import checks  # noqa: E402
from schema.model import Model, SCHEMA  # noqa: E402

VERSION = SCHEMA["properties"]["version"]["const"]
RENAMED = {"schema": "topology"}   # old kind -> new kind; no key changed its name


def levels(level):
    yield level
    for node in level.get("nodes", []):
        if isinstance(node.get("opens"), dict):
            yield from levels(node["opens"])


def migrate(old):
    new = {"version": VERSION, **json.loads(json.dumps(old))}
    for level in levels(new["level"]):
        level["kind"] = RENAMED.get(level.get("kind"), level.get("kind"))
    for level in levels(new["level"]):
        for node in level.get("nodes", []):
            if isinstance(node.get("opens"), dict) and node["opens"].get("kind") != level["kind"]:
                node["link"] = "view"
    # the checker already decides which same-kind open fails to carry its node's edges; mark exactly those nest
    unrefined = {text.split(":")[0] for rule, text in checks.opens(Model(new)) if rule == "opens-interface"}
    for level in levels(new["level"]):
        for node in level.get("nodes", []):
            if node["id"] in unrefined:
                node["link"] = "nest"
    return new


def leaves(value, path="$"):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from leaves(child, f"{path}.{key}")
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, f"{path}[{index}]")
    else:
        yield path, value


def audit(old, new):
    was, now = dict(leaves(old)), dict(leaves(new))
    lost, report, renamed = 0, [], set()
    for path, value in was.items():
        if path in now and now[path] == value:
            continue
        if path.endswith(".kind") and RENAMED.get(value) == now.get(path):
            renamed.add((value, now[path]))
            continue
        lost += 1
        report.append(f"changed: {path}")
    report = [f"renamed: kind {old_kind} -> {new_kind}" for old_kind, new_kind in sorted(renamed)] + report
    for path in now.keys() - was.keys():
        added = (path == "$.version" and now[path] == VERSION) or (path.endswith(".link") and now[path] in ("view", "nest"))
        report.append(f"added: {path} = {now[path]}" if added else f"changed: {path}")
        lost += not added
    print("\n".join(sorted(report, key=lambda line: (not line.startswith("renamed"), line))))
    print(f"facts: {len(was)} old leaf values, {lost} lost")
    return 1 if lost else 0


def read(source):
    return json.load(sys.stdin if source == "-" else open(source, encoding="utf-8"))


def main(args):
    if len(args) == 1 and not args[0].startswith("--"):
        print(json.dumps(migrate(read(args[0])), ensure_ascii=False, indent=1))
        return 0
    if len(args) == 3 and args[0] == "--audit":
        return audit(read(args[1]), read(args[2]))
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
