#!/usr/bin/env python3
"""zoom: check a Schema document against the grammar (assets/schema.json) and the rules the grammar cannot state.

  check-schema.py check doc.json      print each violation as `path: rule: message`, then `ok`, or the error count on stderr
  check-schema.py fixtures            check every document in fixtures/: one named after an error rule must be
                                      rejected by it, one named after a warning rule accepted with that warning,
                                      any other accepted with no warning
  check-schema.py rules               list each rule, error or warning, and what it asks
  check-schema.py ids doc.json        print every node id and edge key (level:from>to#n), one per line
  check-schema.py prose [file.md]     check that schema/'s prose, or the files given, cite the grammar and never restate it

Exit status 0 means ok, 1 a violation, 2 a usage error.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from schema import checks  # noqa: E402
from schema.model import Model, SCHEMA, shape  # noqa: E402

FIXTURES = HERE.parent / "fixtures"
# rules the grammar itself states, by the x-rule of a subschema or a required field
GRAMMAR_RULES = {
    "form": "the document fits the grammar's shape",
    "version-missing": "the document names the grammar version it is written in",
    "kind-unknown": "a level's kind is topology, workflow or state",
    "name-pattern": "ids, slugs, operation and type names follow the grammar's patterns",
    "meta-key": "a meta key is reserved (note, diff, evidence, constraint) or <name>-<format> with a known format",
    "meta-format": "a meta value fits the format its key ends in",
    "evidence-pointer": "evidence is a path:line, a url or a commit sha",
    "constraint-id": "a constraint is <path or url>#<requirement>",
}
NARROW_RULES = {
    "reference": "every id, operation, rule, port and ref a document names points at something",
    "region-without-initial": "each region of a state level names one initial state",
    "sync-unknown-transition": "a sync's when and then name events of its level, and where a state of it",
    "history-outside-superstate": "only a state level opened from a state of its subject has history",
    "view-link-unmarked": "a node that opens a level of another kind is marked link: view",
    "opens-interface": "an unmarked same-kind open maps every edge of its node onto the child's ports",
    "nest-unrefined": "a same-kind open marked nest makes no interface claim",
    "join-without-fork": "a join has two or more edges in, from branches of a fork before it",
}


def violations(data):
    if wrong := shape(data):   # nothing else can be read until the document fits the grammar
        return [(rule, text, "error") for rule, text in wrong]
    return checks.violations(Model(data))


def check(path):
    rows = violations(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    for rule, text, sev in rows:
        print(("" if sev == "error" else "warning ") + checks.line(rule, text))
    errors = sum(1 for _, _, sev in rows if sev == "error")
    # the count goes to stderr, so stdout holds only violation lines, or ok
    print(f"{errors} error(s)", file=sys.stderr) if errors else print("ok")
    return 1 if errors else 0


def rules():
    """Every rule by name: (severity, what it asks)."""
    out = {name: what for name, what in GRAMMAR_RULES.items()}
    out |= {name: what for name, what, _ in checks.RULES if name != "opens"}   # opens states only narrower rules
    out |= NARROW_RULES
    return {name: ("warning" if name in checks.LINT else "error", what) for name, what in out.items()}


def fixtures():
    known, failed, accepted, rejected = rules(), 0, 0, 0
    for f in sorted(FIXTURES.glob("*.json")):
        rows = violations(json.loads(f.read_text(encoding="utf-8")))
        errors = {r for r, _, s in rows if s == "error"}
        warnings = {r for r, _, s in rows if s == "warning"}
        named = f.stem if f.stem in known else None
        if named and known[named][0] == "error":
            good, want = errors == {named}, f"rejected by {named} alone"
        elif named:
            good, want = not errors and named in warnings, f"accepted, warned by {named}"
        else:
            good, want = not errors and not warnings, "accepted with no warning"
        failed += not good
        accepted += not errors
        rejected += bool(errors)
        got = ", ".join(sorted(errors)) and "rejected by " + ", ".join(sorted(errors)) or "accepted" + (", warned by " + ", ".join(sorted(warnings)) if warnings else "")
        print(f"{'ok  ' if good else 'FAIL'}  {f.name}: {got}" + ("" if good else f"; want {want}"))
    unnamed = sorted(set(known) - {f.stem for f in FIXTURES.glob("*.json")})
    for name in unnamed:
        print(f"FAIL  no fixture names rule {name}")
    print(f"fixtures: {accepted} accepted, {rejected} rejected by their named rule" if not failed and not unnamed
          else f"fixtures: {failed + len(unnamed)} failed")
    return 1 if failed or unnamed else 0


def ids(path):
    M = Model(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    print("\n".join(list(M.nodes) + list(M.edges)))
    return 0


KINDS = ("Topology", "Workflow", "State")


def prose(files):
    """Each schema/ document links the grammar, and no line names three or more of its property names, which would
    restate it; semantics.md reads each kind in one paragraph under its own heading."""
    names, out = set(), []

    def collect(node):
        if isinstance(node, dict):
            names.update(node.get("properties", {}))
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)
    collect(SCHEMA)
    docs = [pathlib.Path(f) for f in files] or sorted(HERE.parent.glob("*.md"))
    if missing := [str(d) for d in docs if not d.is_file()]:
        print(f"prose: no such file: {', '.join(missing)}", file=sys.stderr)
        return 2
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        if "assets/schema.json" not in text:
            out.append(f"{doc.name}: links no assets/schema.json")
        for line in text.splitlines():
            if len({w for w in re.findall(r"`([a-z-]+)`", line) if w in names}) >= 3:
                out.append(f"{doc.name}: restates the grammar: {line.strip()[:80]}")
        if doc.name == "semantics.md":
            for kind in KINDS:
                body = re.search(rf"^## {kind}\n\n(.*?)(?=^## |\Z)", text, re.M | re.S)
                if not body or len(body.group(1).strip().split("\n\n")) != 1:
                    out.append(f"{doc.name}: give {kind} one paragraph under ## {kind}")
    print("\n".join(out) or "prose: ok")
    return 1 if out else 0


def main(args):
    cmd = args[0] if args else "help"
    if cmd in ("check", "ids") and len(args) == 2:
        try:
            json.loads(pathlib.Path(args[1]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"{args[1]}: not a JSON document: {e}", file=sys.stderr)
            return 2
    if cmd == "ids" and len(args) == 2 and shape(json.loads(pathlib.Path(args[1]).read_text(encoding="utf-8"))):
        print(f"{args[1]}: breaks the grammar, so it has no ids yet; run check", file=sys.stderr)
        return 2
    if cmd == "check" and len(args) == 2:
        return check(args[1])
    if cmd == "fixtures":
        return fixtures()
    if cmd == "rules":
        for name, (sev, what) in rules().items():
            print(f"{name:24s} {sev:7s} {what}")
        return 0
    if cmd == "ids" and len(args) == 2:
        return ids(args[1])
    if cmd == "prose":
        return prose(args[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
