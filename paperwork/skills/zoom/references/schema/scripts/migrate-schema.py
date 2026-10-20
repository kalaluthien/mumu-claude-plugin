#!/usr/bin/env python3
"""zoom: migrate a document in paperwork's old system.json shape to the Schema (assets/schema.json, version 1).

  migrate-schema.py old.json|-                     print the Schema document
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

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from schema import checks  # noqa: E402
from schema.model import Model, SCHEMA  # noqa: E402

VERSION = SCHEMA["properties"]["version"]["const"]
RENAMED = {"schema": "topology"}   # old kind -> new kind; no key changed its name


def levels(level):
    yield level
    for n in level.get("nodes", []):
        if isinstance(n.get("opens"), dict):
            yield from levels(n["opens"])


def migrate(old):
    new = {"version": VERSION, **json.loads(json.dumps(old))}
    for L in levels(new["level"]):
        L["kind"] = RENAMED.get(L.get("kind"), L.get("kind"))
    for L in levels(new["level"]):
        for n in L.get("nodes", []):
            if isinstance(n.get("opens"), dict) and n["opens"].get("kind") != L["kind"]:
                n["link"] = "view"
    # the checker already decides which same-kind open fails to carry its node's edges; mark exactly those nest
    unrefined = {text.split(":")[0] for rule, text in checks.opens(Model(new)) if rule == "opens-interface"}
    for L in levels(new["level"]):
        for n in L.get("nodes", []):
            if n["id"] in unrefined:
                n["link"] = "nest"
    return new


def leaves(x, path="$"):
    if isinstance(x, dict) and x:
        for k, v in x.items():
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(x, list) and x:
        for i, v in enumerate(x):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, x


def audit(old, new):
    was, now = dict(leaves(old)), dict(leaves(new))
    lost, out, renamed = 0, [], set()
    for p, v in was.items():
        if p in now and now[p] == v:
            continue
        if p.endswith(".kind") and RENAMED.get(v) == now.get(p):
            renamed.add((v, now[p]))
            continue
        lost += 1
        out.append(f"changed: {p}")
    out = [f"renamed: kind {a} -> {b}" for a, b in sorted(renamed)] + out
    for p in now.keys() - was.keys():
        added = (p == "$.version" and now[p] == VERSION) or (p.endswith(".link") and now[p] in ("view", "nest"))
        out.append(f"added: {p} = {now[p]}" if added else f"changed: {p}")
        lost += not added
    print("\n".join(sorted(out, key=lambda l: (not l.startswith("renamed"), l))))
    print(f"facts: {len(was)} old leaf values, {lost} lost")
    return 1 if lost else 0


def read(arg):
    return json.load(sys.stdin if arg == "-" else open(arg, encoding="utf-8"))


def main(args):
    if len(args) == 1 and args[0] != "--audit":
        print(json.dumps(migrate(read(args[0])), ensure_ascii=False, indent=1))
        return 0
    if len(args) == 3 and args[0] == "--audit":
        return audit(read(args[1]), read(args[2]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
