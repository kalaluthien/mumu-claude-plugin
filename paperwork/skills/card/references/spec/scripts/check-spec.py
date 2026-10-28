#!/usr/bin/env python3
"""Check a grading spec against the grammar (assets/rubric-schema.json) and the rules it cannot state.

usage: check-spec.py check spec.json      print each violation as `path: rule: message`, then `ok`, or the error count on stderr
       check-spec.py weights spec.json    print each tier's derived epsilon beside the delta and judge_error it comes from
       check-spec.py fixtures             check every spec in fixtures/: one named after an error rule (or a rule and more
                                          words) must be rejected by it alone, one named after a warning rule accepted with
                                          that warning, any other accepted with no warning
       check-spec.py rules                list each rule, error or warning, and what it asks
       check-spec.py prose [file.md]      check that spec/'s prose, or the files given, link the grammar and never restate it

Exit status 0 means ok, 1 a violation, 2 a usage error.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5] / "lib"))

from rubric.model import weights  # noqa: E402
from rubric.spec import GRAMMAR, RULES, SCHEMA, line, violations  # noqa: E402

FIXTURES = HERE.parent / "fixtures"
# read() returns it for a file it cannot parse, since a parsed spec may be null
UNREAD = object()


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"{path}: not a JSON document: {e}", file=sys.stderr)
        return UNREAD


def check(path):
    if (spec := read(path)) is UNREAD:
        return 2
    rows = violations(spec)
    for rule, where, message, severity in rows:
        print(("" if severity == "error" else "warning ") + line(rule, where, message))
    errors = sum(1 for *_, row_severity in rows if row_severity == "error")
    # the count goes to stderr, so stdout holds only violation lines, or ok
    print(f"{errors} error(s)", file=sys.stderr) if errors else print("ok")
    return 1 if errors else 0


def show_weights(path):
    if (spec := read(path)) is UNREAD:
        return 2
    if errors := [violation for violation in violations(spec) if violation[3] == "error"]:
        for rule, where, message, _ in errors:
            print(line(rule, where, message))
        print(f"{len(errors)} error(s); weights need a spec that checks", file=sys.stderr)
        return 1
    tiers, epsilons = spec["tiers"], weights(spec)
    for tier, epsilon in zip(tiers[:-1], epsilons):
        print(f"{tier['id']}: epsilon {epsilon:.6g} delta {tier['delta']:g} judge_error {tier['judge_error']:g}")
    print(f"{tiers[-1]['id']}: epsilon 1")
    print("Each epsilon is the least weight, with a 5% margin, at which a tier-score difference of delta, seen through "
          "a judge that flips judge_error of its verdicts, outweighs every lower tier at once; the reward is the sum "
          "of epsilon times tier score.")
    return 0


def named_rule(stem):
    """The rule a fixture is named after: the longest rule its name equals or opens with, then a dash."""
    hits = [rule for rule in RULES if stem == rule or stem.startswith(rule + "-")]
    return max(hits, key=len) if hits else None


def fixtures():
    failed = accepted = rejected = 0
    files = sorted(FIXTURES.glob("*.json"))
    for fixture_file in files:
        rows = violations(json.loads(fixture_file.read_text(encoding="utf-8")))
        errors = {rule for rule, *_, severity in rows if severity == "error"}
        warnings = {rule for rule, *_, severity in rows if severity == "warning"}
        named = named_rule(fixture_file.stem)
        if named and RULES[named][0] == "error":
            good, want = errors == {named}, f"rejected by {named} alone"
        elif named:
            good, want = not errors and warnings == {named}, f"accepted, warned by {named} alone"
        else:
            good, want = not errors and not warnings, "accepted with no warning"
        failed += not good
        accepted += not errors
        rejected += bool(errors)
        got = ("rejected by " + ", ".join(sorted(errors))) if errors else "accepted" + (", warned by " + ", ".join(sorted(warnings)) if warnings else "")
        print(f"{'ok  ' if good else 'FAIL'}  {fixture_file.name}: {got}" + ("" if good else f"; want {want}"))
    unnamed = sorted(set(RULES) - {named_rule(fixture.stem) for fixture in files})
    for name in unnamed:
        print(f"FAIL  no fixture names rule {name}")
    print(f"fixtures: {accepted} accepted, {rejected} rejected by their named rule" if not failed and not unnamed
          else f"fixtures: {failed + len(unnamed)} failed")
    return 1 if failed or unnamed else 0


def blocks(text):
    """Paragraphs, each list item and each table row on its own, since each is one statement."""
    out = []
    for paragraph in re.split(r"\n\s*\n", text):
        current = []
        for text_line in paragraph.splitlines():
            if re.match(r"\s*([-*|]|\d+\.)\s", text_line) and current:
                out.append(" ".join(current))
                current = []
            current.append(text_line)
        out.append(" ".join(current))
    return out


def prose(files):
    """Each file links the grammar by a path relative to itself, and no paragraph, list item or table row names three
    or more of its property names in backticks, which would restate it."""
    names = set()

    def collect(node):
        if isinstance(node, dict):
            names.update(node.get("properties", {}))
            for child in node.values():
                collect(child)
        elif isinstance(node, list):
            for child in node:
                collect(child)
    collect(SCHEMA)
    documents = [pathlib.Path(file_path) for file_path in files] or sorted(HERE.parent.glob("*.md"))
    if missing := [str(candidate) for candidate in documents if not candidate.is_file()]:
        print(f"prose: no such file: {', '.join(missing)}", file=sys.stderr)
        return 2
    out = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)\s#]+)", text)
        if not any(not link.startswith("/") and (document.resolve().parent / link).resolve() == GRAMMAR for link in links):
            out.append(f"{document}: links no assets/rubric-schema.json by a path relative to it")
        for block in blocks(text):
            if len(hit := {word for word in re.findall(r"`([a-z_]+)`", block) if word in names}) >= 3:
                out.append(f"{document}: restates the grammar ({', '.join(sorted(hit))}): {block.strip()[:80]}")
    print("\n".join(out) or "prose: ok")
    return 1 if out else 0


def main(args):
    command = args[0] if args else "help"
    if command == "check" and len(args) == 2:
        return check(args[1])
    if command == "weights" and len(args) == 2:
        return show_weights(args[1])
    if command == "fixtures" and len(args) == 1:
        return fixtures()
    if command == "rules" and len(args) == 1:
        for name, (severity, description) in RULES.items():
            print(f"{name:24s} {severity:7s} {description}")
        return 0
    if command == "prose":
        return prose(args[1:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
