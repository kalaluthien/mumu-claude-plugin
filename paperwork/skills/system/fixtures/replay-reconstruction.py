#!/usr/bin/env python3
"""Replay the contract score on each example and fail when a planted fault does not lower the side it belongs to.

usage: replay-reconstruction.py

For each `../examples/*/contract.json`, scored against the repository's root, three copies are scored again: one whose first
quoted value its sources hold gets a digit more, which must lower precision by one or more and exit 1; one whose first answered
question is left to a gap, which must lower recall by one and leave precision as it was; and one whose first source is given a
path that is no file, which must print a `missing path` line and exit 1. It prints one PASS or FAIL line per example with both
scores, then PASS or FAIL."""
import copy
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
SCORE = HERE.parent / "scripts" / "score-contract.py"


def scored(contract):
    """The exit status, the recall and precision pairs and the output of the score call on CONTRACT."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "contract.json"
        path.write_text(json.dumps(contract))
        done = subprocess.run([sys.executable, str(SCORE), str(path), "--root", str(ROOT)], capture_output=True, text=True)
    pairs = [tuple(map(int, pair)) for pair in re.findall(r"^(?:recall|precision) (\d+) of (\d+)", done.stdout, re.MULTILINE)]
    return done.returncode, pairs, done.stdout


def planted(contract, missing):
    """A copy of CONTRACT whose first quoted value that is not among MISSING holds one digit more, or None when it quotes none."""
    copied = copy.deepcopy(contract)
    done = []

    def changed(value, name):
        if isinstance(value, dict):
            return {key: changed(part, name) for key, part in value.items()}
        if isinstance(value, list):
            return [changed(part, name) for part in value]
        for quote in re.finditer(r"`([^`]+)`", value) if isinstance(value, str) and not done else ():
            if len(quote.group(1).strip()) > 1 and "<" not in quote.group(1) and f"{name}: `{quote.group(1).strip()}`" not in missing:
                done.append(name)
                return value[:quote.end(1)] + "7" + value[quote.end(1):]
        return value

    records = [element for kind in ("nodes", "edges", "areas") for element in copied.get(kind, [])]
    for record in records + copied.get("properties", []):
        for name in ("label", "purpose", "statement", "info") if record.get("evidence") else ():
            if name in record:
                record[name] = changed(record[name], record["id"])
    return copied if done else None


def faults(contract):
    """What the score call gets wrong on CONTRACT and its three copies, then the line of its two scores."""
    status, pairs, printed = scored(contract)
    if status not in (0, 1) or len(pairs) != 2:
        return [f"the score call exits {status} and prints {len(pairs)} scores"], ""
    (answered, asked), (found, quoted) = pairs
    found_faults = []
    wrong = planted(contract, printed)
    if wrong is None:
        found_faults.append("it quotes no value its sources hold, so precision has nothing to lose")
    else:
        status, changed, _ = scored(wrong)
        if status != 1 or len(changed) != 2 or changed[1][0] >= found or changed[0] != pairs[0]:
            found_faults.append(f"a quoted value with a digit more leaves precision at {changed[1:]} of {pairs[1]}, exit {status}")
    gap = next((item["id"] for item in contract.get("properties", []) if item["kind"] == "gap"), None)
    open_question = copy.deepcopy(contract)
    first = next((question for question in open_question.get("questions", []) if question.get("answers")), None)
    if first is None or gap is None:
        found_faults.append("it holds no answered question or no gap to leave one to")
    else:
        del first["answers"]
        first["gap"] = gap
        _, changed, _ = scored(open_question)
        if changed != [(answered - 1, asked), (found, quoted)]:
            found_faults.append(f"a question left to a gap gives {changed}, expected recall {answered - 1} of {asked} and precision unchanged")
    moved = copy.deepcopy(contract)
    moved["sources"][0]["path"] += ".gone"
    status, _, printed = scored(moved)
    if status != 1 or f"missing path {moved['sources'][0]['id']}: " not in printed:
        found_faults.append(f"a source path that is no file is not reported, exit {status}")
    return found_faults, f"recall {answered} of {asked}, precision {found} of {quoted}"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = 0
    examples = sorted((HERE.parent / "examples").glob("*/contract.json"))
    for path in examples:
        found, scores = faults(json.loads(path.read_text()))
        failed += bool(found)
        print(f"FAIL {path.parent.name}: {'; '.join(found)}" if found else f"PASS {path.parent.name}: {scores}")
    if not examples:
        failed += 1
        print("FAIL no example contract to score")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
