#!/usr/bin/env python3
"""drill-it: write and check a system model, and prove its rules with Alloy.

  check-system.py new system.json                 write a valid minimal system model
  check-system.py rules                           list the system checks and the plan's parameters
  check-system.py plan system.json                print the plan in effect, marking what differs from the defaults
  check-system.py check system.json [--prove] [--only a,b]   run the checks; --prove adds Alloy (once, at the end)
  check-system.py alloy system.json out.als       write the model as an Alloy 6 module
  check-system.py alloy --fetch                   download Alloy 6 for the alloy check (needs Java)

A finding line is a defect of the system the model describes (a must rule its behaviour can break), reported
and kept, never fixed by bending the model. Alloy never fails a run: what keeps it from answering is a note and an `unproved:` status. Exit status 0 means ok, 1 errors.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))

from system import checks  # noqa: E402
from system import plan as params  # noqa: E402
from system.model import dump, load, shape  # noqa: E402


def check(path, prove=False, only=None):
    """Errors fail, lint warns, findings are reported; with --prove the last line says whether Alloy checked the model."""
    if refusal := checks.unknown(only, checks.CHECKS):
        print(refusal)
        return 2
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if wrong := shape(data):   # the file's shape comes first: nothing else can be read until it fits
        print("FAIL  form\n" + "\n".join(f"      - {p}" for p in wrong) + f"\n{len(wrong)} problem(s)")
        return 1
    M = load(path)
    lines, failed = checks.report(checks.run(M, prove, only), M)
    print("\n".join(lines))
    items = M.m["scenarios"] + M.m["operations"] + M.m["rules"] + list(M.nodes.values())
    print(f"info  {sum(1 for x in items if x.get('refs'))}/{len(items)} elements cite a source")
    if failed:
        print(f"{failed} problem(s)")
        return 1
    print(f"ok ({M.alloy_status})" if M.alloy_status.startswith("unproved") else "ok")
    return 0


def option(args, name):
    return args[args.index(name) + 1] if name in args else None


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "new":   # a valid start: one component level of two parts and one relation, and nothing else yet
        start = {"title": "System", "plan": {"intent": "The user's question, in one sentence."},
                 "scenarios": [], "operations": [], "rules": [],
                 "level": {"kind": "schema", "title": "System", "why": "What the system is made of.",
                           "nodes": [{"id": "a", "label": "Part", "what": "One sentence."},
                                     {"id": "b", "label": "Other part", "what": "One sentence."}],
                           "edges": [{"from": "a", "to": "b", "label": "uses", "what": "One sentence."}]}}
        pathlib.Path(args[1]).write_text(dump(start) + "\n", encoding="utf-8")
        print("wrote", args[1], "(fields: assets/system-schema.json)")
        return 0
    if cmd == "rules":
        for name, rule, _ in checks.RULES:
            print(f"{name:13s} {'lint ' if name in checks.LINT else 'error'} {rule}")
        print()
        for name, (default, allowed, what) in params.DEFAULTS.items():
            print(f"{name:13s} {json.dumps(default, ensure_ascii=False):30s} {what}")
        return 0
    if cmd == "plan":
        for name, value in load(args[1]).plan.items():
            mark = "*" if value != params.DEFAULTS[name][0] else " "
            print(f"{mark} {name:11s} {json.dumps(value, ensure_ascii=False)}")
        return 0
    if cmd == "check":
        only = option(args, "--only")
        return check(args[1], "--prove" in args, only and only.split(","))
    if cmd == "alloy":
        from system import prover as alloy
        if "--fetch" in args:
            print("wrote", alloy.fetch())
            return 0
        als, W, _ = alloy.translate(load(args[1]))
        pathlib.Path(args[2]).write_text(als, encoding="utf-8")
        print("\n".join(W.problems) or f"wrote {args[2]}")
        return 1 if W.problems else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
