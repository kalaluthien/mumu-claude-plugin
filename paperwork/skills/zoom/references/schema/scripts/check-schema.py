#!/usr/bin/env python3
"""Check a Schema document against the grammar (assets/schema.json) and the rules the grammar cannot state.

usage: check-schema.py check doc.json [--root DIR]   print each violation as `path: rule: message`, then `ok`, or the
                                                     error count on stderr; with --root, each `path:line` must point
                                                     inside its file under DIR
       check-schema.py fixtures                      check every document in fixtures/: one named after a rule must be
                                                     rejected by it alone, any other accepted
       check-schema.py rules                         list each rule and what it asks
       check-schema.py ids doc.json                  print every node id and edge key (level:from>to#n), one per line

Exit status 0 means ok, 1 a violation, 2 a usage error.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5] / "lib"))

from schema import checks  # noqa: E402
from schema.model import Model, shape  # noqa: E402

FIXTURES = HERE.parent / "fixtures"
ROOT = pathlib.Path(__file__).resolve().parents[6]   # fixtures cite this repository's files
# rules the grammar itself states, by the x-rule of a subschema or a required field
GRAMMAR_RULES = {
    "form": "the document fits the grammar's shape",
    "version-missing": "the document names the grammar version it is written in",
    "name-pattern": "ids, slugs and type names follow the grammar's patterns",
    "source-missing": "every node, edge and rule names its source",
    "description-missing": "every node, edge and rule carries a description",
    "source-pointer": "a source is path:line, or a url",
}


def violations(data, root=None):
    # nothing else can be read until the document fits the grammar
    return shape(data) or checks.violations(Model(data), root)


def line(rule, text):
    """`path: rule: message`, the path being what the problem's sentence opens with."""
    where, _, message = text.partition(": ")
    # a sentence that opens with words before its first colon is about the whole document
    return f"{where}: {rule}: {message}" if message and not re.search(r"\s", where) else f"schema: {rule}: {text}"


def check(path, root):
    rows = violations(json.loads(pathlib.Path(path).read_text(encoding="utf-8")), root)
    for rule, text in rows:
        print(line(rule, text))
    # the count goes to stderr, so stdout holds only violation lines, or ok
    print(f"{len(rows)} error(s)", file=sys.stderr) if rows else print("ok")
    return 1 if rows else 0


def rules():
    return GRAMMAR_RULES | {name: what for name, _, what in checks.RULES} | {"source-unresolved": checks.UNRESOLVED}


def fixtures():
    known, failed = rules(), 0
    for fixture_path in sorted(FIXTURES.glob("*.json")):
        errors = {rule for rule, _ in violations(json.loads(fixture_path.read_text(encoding="utf-8")), ROOT)}
        named = next((rule for rule in known if fixture_path.stem == rule or fixture_path.stem.startswith(f"{rule}-")), None)
        good = errors == {named} if named else not errors
        failed += not good
        got = "rejected by " + ", ".join(sorted(errors)) if errors else "accepted"
        print(f"{'ok  ' if good else 'FAIL'}  {fixture_path.name}: {got}" + ("" if good else f"; want {'rejected by ' + named + ' alone' if named else 'accepted'}"))
    unnamed = sorted(set(known) - {path.stem for path in FIXTURES.glob("*.json")})
    for name in unnamed:
        print(f"FAIL  no fixture names rule {name}")
    print("fixtures: ok" if not failed and not unnamed else f"fixtures: {failed + len(unnamed)} failed")
    return 1 if failed or unnamed else 0


def ids(path):
    model = Model(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    print("\n".join(list(model.nodes) + list(model.edges)))
    return 0


def main(args):
    root = None
    if len(args) == 4 and args[0] == "check" and args[2] == "--root":
        root, args = args[3], args[:2]
    command = args[0] if args else "help"
    if command in ("check", "ids") and len(args) == 2:
        try:
            data = json.loads(pathlib.Path(args[1]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"{args[1]}: not a JSON document: {e}", file=sys.stderr)
            return 2
        if command == "check":
            return check(args[1], root)
        if shape(data):
            print(f"{args[1]}: breaks the grammar, so it has no ids yet; run check", file=sys.stderr)
            return 2
        return ids(args[1])
    if command == "fixtures" and len(args) == 1:
        return fixtures()
    if command == "rules" and len(args) == 1:
        for name, what in rules().items():
            print(f"{name:24s} {what}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
