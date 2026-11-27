#!/usr/bin/env python3
"""Replay a change to the tag catalogue both skills share on a copy of the plugin, and fail when a skill misses it or writes a shared entry again.

usage: replay-shared-tags.py

On a copy of the plugin whose `../tags.json` alone gives the `service` node's `responsibilities` item a new label, both skills' `tags`
calls and the page runners' `tags` reader in `../check-step.cjs` must give it, both checkers must accept system's `parcel-locker.json` and
flow's `examples/name-lookup/contract.json`, system's also under `--tags` its own catalogue, whose `service` nodes hold that item, and both `make-page.py`
builds must carry it in the page's tags block; and no skill's own catalogue may write again the forms, a tag or a common item the shared
catalogue holds. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

PLUGIN = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = {"system": "skills/system/fixtures/parcel-locker.json", "flow": "skills/flow/examples/name-lookup/contract.json"}
TAG, ITEM, LABEL = "service", "responsibilities", "planted duties"


def run(*command):
    done = subprocess.run([sys.executable, *map(str, command)], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def relabelled(copied):
    """Give the shared item its new label in COPIED's shared catalogue alone, or say why it cannot."""
    path = copied / "lib/tags.json"
    if not path.exists():
        return "the plugin holds no shared catalogue `lib/tags.json`"
    shared = json.loads(path.read_text())
    items = [item for item in shared.get("node", {}).get(TAG, {}).get("items", []) if item["name"] == ITEM]
    if not items:
        return f"the shared catalogue holds no `{TAG}` node item `{ITEM}`"
    items[0]["label"] = LABEL
    path.write_text(json.dumps(shared, indent=1) + "\n")
    return None


def reached(copied, skill, scratch):
    """Each way SKILL on COPIED misses the new label."""
    script = copied / "skills" / skill / "scripts"
    found = []
    _, printed = run(script / "check-contract.py", "tags")
    if f"{ITEM} ({LABEL})" not in printed:
        found.append(f"its `tags` call does not print `{ITEM} ({LABEL})`")
    read = subprocess.run(["node", "-e", "console.log(JSON.stringify(require(process.argv[1]).tags(process.argv[2])))", copied / "lib/check-step.cjs",
                           copied / "skills" / skill / "assets/tags.json"], capture_output=True, text=True).stdout
    if f'"label":"{LABEL}"' not in read:
        found.append(f"the page runners' `tags` reader does not give `{ITEM}` the label `{LABEL}`")
    fixture = copied / FIXTURES[skill]
    if not any(node["tag"] == TAG and ITEM in node.get("info", {}) for node in json.loads(fixture.read_text())["nodes"]):
        found.append(f"{fixture.name} holds no `{TAG}` node with `{ITEM}`")
    status, printed = run(script / "check-contract.py", "check", fixture)
    if status:
        found.append(f"its checker refuses {fixture.name}: {printed.strip()[:300]}")
    if skill == "system":
        status, printed = run(script / "check-contract.py", "check", fixture, "--tags", copied / "skills/system/assets/tags.json")
        if status:
            found.append(f"its checker refuses {fixture.name} under `--tags` its own catalogue: {printed.strip()[:300]}")
    page = pathlib.Path(scratch) / f"{skill}.html"
    status, printed = run(script / "make-page.py", fixture, page)
    block = re.search(r'<script type="application/json" id="page-tags">(.*?)</script>', page.read_text(), re.S) if page.exists() else None
    tags = json.loads(block.group(1)) if block else {}
    labels = [item.get("label") for item in tags.get("node", {}).get(TAG, {}).get("items", []) if item.get("name") == ITEM]
    if status or labels != [LABEL]:
        found.append(f"its page's tags block labels `{ITEM}` {labels}, exit {status}")
    return found


def repeated():
    """Each form list, tag or common item a skill's own catalogue writes that the shared catalogue already holds."""
    path = PLUGIN / "lib/tags.json"
    if not path.exists():
        return ["the plugin holds no shared catalogue `lib/tags.json`"]
    shared = json.loads(path.read_text())
    found = []
    for skill in FIXTURES:
        own = json.loads((PLUGIN / "skills" / skill / "assets/tags.json").read_text())
        if "forms" in own and own["forms"] == shared["forms"]:
            found.append(f"{skill} writes the shared forms")
        for kind in sorted(set(own) - {"forms", "common"}):
            found += [f"{skill} writes the {kind} tag {name}" for name in sorted(set(own[kind]) & set(shared.get(kind, {})))]
        for kind, items in sorted(own.get("common", {}).items()):
            names = {item["name"] for item in items} & {item["name"] for item in shared.get("common", {}).get(kind, [])}
            found += [f"{skill} writes the common {kind} item {name}" for name in sorted(names)]
    return found


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        copied = pathlib.Path(scratch) / "paperwork"
        shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        reason = relabelled(copied)
        for skill in FIXTURES:
            missed = [reason] if reason else reached(copied, skill, scratch)
            print(f"FAIL {skill} reach: {'; '.join(missed)}" if missed else f"PASS {skill} reach")
            failed |= bool(missed)
    twice = repeated()
    print(f"FAIL written once: {'; '.join(twice)}" if twice else "PASS written once")
    failed |= bool(twice)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
