#!/usr/bin/env python3
"""Replay every shipped contract's claims through the calls and pages that read them, and fail when one still holds properties or reads a claim wrongly.

usage: replay-claim-records.py

Every contract of both skills' `examples/` and `fixtures/`, and every copy in `contract-copies.json`, must hold `claims` and no
`properties`, each claim a guarantee or an assumption; for each system example and fixture, `read` must say each claim's kind, strength
and status, the written one or, under `paths`, the one the checker settles, and `score-contract.py` must leave out of its recall, and
list, exactly the questions whose every answer is a claim with a fault, and list as missing a quote a claim of system's own example takes
from a source that does not hold it; each system example's page, built again, must equal the shipped one; and system's `run-page.cjs
badges counts` and flow's `run-page.cjs interaction plan` must pass, which draw each claim's status as a badge on its records and each
mark in its area's colour. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import json
import pathlib
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = LIB.parent
ROOT = PLUGIN.parent
SKILLS = PLUGIN / "skills"
KINDS = ("guarantee", "assumption")
STATUSES = ("holds", "fails", "conflicting", "unknown")
QUOTE = "planted-text-no-source-holds"
QUOTED = SKILLS / "system/examples/self/contract.json"


def run(*command):
    done = subprocess.run([*map(str, command)], capture_output=True, text=True, cwd=ROOT)
    return done.returncode, done.stdout + done.stderr


def shipped():
    """Each shipped whole contract of both skills, as (skill, path)."""
    found = []
    for skill in ("system", "flow"):
        for path in sorted((SKILLS / skill).glob("examples/*/contract.json")) + sorted((SKILLS / skill).glob("fixtures/*.json")):
            value = json.loads(path.read_text())
            if isinstance(value, dict) and "levels" in value:
                found.append((skill, path))
    return found


def form_faults(contract):
    if "properties" in contract:
        return ["holds `properties`"]
    if not contract.get("claims"):
        return ["holds no `claims`"]
    return [f"claim {claim.get('id')} is a {claim.get('kind')}" for claim in contract["claims"] if claim.get("kind") not in KINDS]


def copy_faults(skill):
    """Each copy of SKILL's `contract-copies.json` that changes a `properties` record."""
    held = json.loads((SKILLS / skill / "fixtures/contract-copies.json").read_text())
    return [f"copy {name} changes `properties`" for named in held.values() for name, changes in named.items()
            if any(change[0][:1] == ["properties"] for change in changes)]


def read_faults(path, contract):
    _, printed = run(sys.executable, SKILLS / "system/scripts/check-contract.py", "read", path)
    found = []
    for claim in contract["claims"]:
        opening = f"{claim['kind']} {claim['id']} ({claim.get('strength', 'must')}, "
        lines = [line for line in printed.splitlines() if line.startswith(opening)]
        said = lines[0][len(opening):].split(")", 1)[0] if lines else None
        wanted = STATUSES if "paths" in claim else (claim.get("status", "holds"),)
        if said not in wanted:
            found.append(f"`read` says claim {claim['id']} as {lines[:1] or 'nothing'}, wanting status {' or '.join(wanted)}")
    return found


def score_faults(path, contract):
    faulted = {claim["id"] for claim in contract["claims"] if "fault" in claim}
    questions = contract.get("questions", [])
    wanted = sorted(question["id"] for question in questions if question.get("answers") and set(question["answers"]) <= faulted)
    _, printed = run(sys.executable, SKILLS / "system/scripts/score-contract.py", path, "--root", ROOT)
    lines = printed.splitlines()
    recall = next((line for line in lines if line.startswith("recall ")), "")
    listed = []
    if recall:
        for line in lines[lines.index(recall) + 1:]:
            if not line.startswith("  "):
                break
            listed.append(line.strip().split(":", 1)[0])
    found = []
    if not recall.startswith(f"recall {len(questions) - len(wanted)} of {len(questions)}"):
        found.append(f"`score-contract.py` says `{recall}`, wanting recall {len(questions) - len(wanted)} of {len(questions)}")
    if sorted(listed) != wanted:
        found.append(f"`score-contract.py` lists {sorted(listed)} as left to a claim, wanting {wanted}")
    return found


def quote_faults(scratch):
    """Whether `score-contract.py` lists a quote a claim of system's own example takes from a source that does not hold it."""
    contract = json.loads(QUOTED.read_text())
    planted = pathlib.Path(scratch) / "quoted.json"
    claim = {"id": "planted-quote", "evidence": [contract["sources"][0]["id"]], "statement": f"It holds `{QUOTE}`."}
    planted.write_text(json.dumps({**contract, "claims": contract["claims"] + [claim]}))
    _, printed = run(sys.executable, SKILLS / "system/scripts/score-contract.py", planted, "--root", ROOT)
    return [] if f"  planted-quote: `{QUOTE}`" in printed.splitlines() else [f"`score-contract.py` misses the quote `{QUOTE}` of a claim whose source does not hold it"]


def page_faults(path, scratch):
    built = pathlib.Path(scratch) / f"{path.parent.name}.html"
    status, printed = run(sys.executable, SKILLS / "system/scripts/make-page.py", path, built)
    if status or not built.exists():
        return [f"`make-page.py` fails: {printed.strip()[:300]}"]
    return [] if built.read_bytes() == (path.parent / "page.html").read_bytes() else ["its page, built again, differs from the shipped page.html"]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False

    def report(step, faults):
        nonlocal failed
        print(f"FAIL {step}: {'; '.join(faults)}" if faults else f"PASS {step}")
        failed |= bool(faults)

    with tempfile.TemporaryDirectory() as scratch:
        for skill, path in shipped():
            contract = json.loads(path.read_text())
            faults = form_faults(contract)
            if not faults and skill == "system":
                faults = read_faults(path, contract) + score_faults(path, contract)
                if path.name == "contract.json":
                    faults += page_faults(path, scratch)
            report(f"{skill} {path.relative_to(SKILLS / skill)}", faults)
        report("system quotes", quote_faults(scratch))
    for skill in ("system", "flow"):
        report(f"{skill} copies", copy_faults(skill))
    for skill, steps in (("system", ("badges", "counts")), ("flow", ("interaction", "plan"))):
        status, printed = run("node", SKILLS / skill / "scripts/run-page.cjs", *steps)
        report(f"{skill} page", [line for line in printed.splitlines() if line.startswith("FAIL")] or ([] if status == 0 else [f"exit {status}"]))
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
