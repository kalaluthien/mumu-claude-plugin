#!/usr/bin/env python3
"""quiz: check a grading spec against the grammar (assets/rubric.schema.json) and the rules it cannot state.

  check-spec.py check spec.json      print each violation as `path: rule: message`, then `ok`, or the error count on stderr
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
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from quiz.model import weights  # noqa: E402
from quiz.spec import GRAMMAR, RULES, SCHEMA, line, violations  # noqa: E402

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
    for rule, where, message, sev in rows:
        print(("" if sev == "error" else "warning ") + line(rule, where, message))
    errors = sum(1 for *_, sev in rows if sev == "error")
    # the count goes to stderr, so stdout holds only violation lines, or ok
    print(f"{errors} error(s)", file=sys.stderr) if errors else print("ok")
    return 1 if errors else 0


def show_weights(path):
    if (spec := read(path)) is UNREAD:
        return 2
    if errors := [r for r in violations(spec) if r[3] == "error"]:
        for rule, where, message, _ in errors:
            print(line(rule, where, message))
        print(f"{len(errors)} error(s); weights need a spec that checks", file=sys.stderr)
        return 1
    tiers, eps = spec["tiers"], weights(spec)
    for tier, e in zip(tiers[:-1], eps):
        print(f"{tier['id']}: epsilon {e:.6g} delta {tier['delta']:g} judge_error {tier['judge_error']:g}")
    print(f"{tiers[-1]['id']}: epsilon 1")
    print("Each epsilon is the least weight, with a 5% margin, at which a tier-score difference of delta, seen through "
          "a judge that flips judge_error of its verdicts, outweighs every lower tier at once; the reward is the sum "
          "of epsilon times tier score.")
    return 0


def named_rule(stem):
    """The rule a fixture is named after: the longest rule its name equals or opens with, then a dash."""
    hits = [r for r in RULES if stem == r or stem.startswith(r + "-")]
    return max(hits, key=len) if hits else None


def fixtures():
    failed = accepted = rejected = 0
    files = sorted(FIXTURES.glob("*.json"))
    for f in files:
        rows = violations(json.loads(f.read_text(encoding="utf-8")))
        errors = {r for r, *_, s in rows if s == "error"}
        warnings = {r for r, *_, s in rows if s == "warning"}
        named = named_rule(f.stem)
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
        print(f"{'ok  ' if good else 'FAIL'}  {f.name}: {got}" + ("" if good else f"; want {want}"))
    unnamed = sorted(set(RULES) - {named_rule(f.stem) for f in files})
    for name in unnamed:
        print(f"FAIL  no fixture names rule {name}")
    print(f"fixtures: {accepted} accepted, {rejected} rejected by their named rule" if not failed and not unnamed
          else f"fixtures: {failed + len(unnamed)} failed")
    return 1 if failed or unnamed else 0


def blocks(text):
    """Paragraphs, each list item and each table row on its own, since each is one statement."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        cur = []
        for ln in para.splitlines():
            if re.match(r"\s*([-*|]|\d+\.)\s", ln) and cur:
                out.append(" ".join(cur))
                cur = []
            cur.append(ln)
        out.append(" ".join(cur))
    return out


def prose(files):
    """Each file links the grammar by a path relative to itself, and no paragraph, list item or table row names three
    or more of its property names in backticks, which would restate it."""
    names = set()

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
    out = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)\s#]+)", text)
        if not any(not link.startswith("/") and (doc.resolve().parent / link).resolve() == GRAMMAR for link in links):
            out.append(f"{doc}: links no assets/rubric.schema.json by a path relative to it")
        for block in blocks(text):
            if len(hit := {w for w in re.findall(r"`([a-z_]+)`", block) if w in names}) >= 3:
                out.append(f"{doc}: restates the grammar ({', '.join(sorted(hit))}): {block.strip()[:80]}")
    print("\n".join(out) or "prose: ok")
    return 1 if out else 0


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "check" and len(args) == 2:
        return check(args[1])
    if cmd == "weights" and len(args) == 2:
        return show_weights(args[1])
    if cmd == "fixtures" and len(args) == 1:
        return fixtures()
    if cmd == "rules" and len(args) == 1:
        for name, (sev, what) in RULES.items():
            print(f"{name:24s} {sev:7s} {what}")
        return 0
    if cmd == "prose":
        return prose(args[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
