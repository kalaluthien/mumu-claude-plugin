#!/usr/bin/env python3
"""Write each open GitHub issue's native links into its body, since every board read takes links from bodies: a sub-issue as a
`N. [task] #n <title>` line of its parent's Definition of done, a `blocked by` link as a `depends on:` entry; then drop the retired
kind label. Each body changes by edit-issue-body.py, so its diff lands as a comment. A closed parent of an open part gains its line
too, by the same edit, which opens it again. A body link GitHub lacks is linked natively. It ends with the link gaps left, as the
manager's heartbeat lists them.

usage: sync-task-links.py [--dry-run]"""
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import board_github  # noqa: E402
import issue_state  # noqa: E402
import task_links  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DONE_HEADING = next(heading for heading, role in issue_state.SECTIONS.items() if role == "done")
DEPENDS = issue_state.WORD["depends"]
WHY = "DECIDED: links written from GitHub's native ones, since the board now reads them from bodies (#1187)"


def with_parts(body, lines):
    """BODY with LINES appended to its Definition of done, numbered on from its last item; the section is added when absent."""
    match = re.search(rf"^## {re.escape(DONE_HEADING)}\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not match:
        return body.rstrip("\n") + f"\n\n## {DONE_HEADING}\n\n" + "".join(f"{i}. {line}\n" for i, line in enumerate(lines, 1))
    numbers = [int(n) for n in re.findall(r"^\s*(\d+)\.", match.group(1), re.M)]
    start = max(numbers, default=0) + 1
    section = match.group(1).rstrip("\n") + "\n" + "".join(f"{i}. {line}\n" for i, line in enumerate(lines, start))
    rest = body[match.end():]
    return body[:match.start(1)] + section + ("\n" + rest if rest else "")


def with_depends(body, numbers):
    """BODY whose `depends on` line also names NUMBERS, in its teamwork block, which is added before the Definition of done when absent."""
    entry = " ".join(f"#{n}" for n in numbers)
    block = issue_state.DATA.search(body)
    if block:
        inner = block.group(1)
        line = re.search(rf"^{re.escape(DEPENDS)}:(.*)$", inner, re.M)
        inner = (inner[:line.end()] + f" {entry}" + inner[line.end():]) if line else inner + f"{DEPENDS}: {entry}\n"
        return body[:block.start(1)] + inner + body[block.end(1):]
    fence = f"```teamwork\n{DEPENDS}: {entry}\n```\n"
    heading = re.search(rf"^## {re.escape(DONE_HEADING)}$", body, re.M)
    return body[:heading.start()] + fence + "\n" + body[heading.start():] if heading else body.rstrip("\n") + "\n\n" + fence


def scope_of(node):
    names = [label["name"] for label in (node.get("labels") or {}).get("nodes", [])]
    return next((name for name in names if name.startswith("scope:")), "no scope")


def plan(nodes):
    """{number: (scope, open, new parts as [(n, title)], new depends, drops the label, links to make natively)} for each issue whose
    body, labels or native links change."""
    by_number = {node["number"]: node for node in nodes}
    changes = {}

    def change(number):
        if number not in changes:
            node = by_number.get(number)
            changes[number] = {"scope": scope_of(node) if node else None, "open": node is not None, "parts": [], "depends": [], "label": False, "native": []}
        return changes[number]

    for node in (node for node in nodes if "native" in node):
        native, number = node["native"], node["number"]
        said = task_links.parts(node["body"])
        titles = dict(native["titles"])
        if native["total"] > len(native["parts"]):
            listed = board.get(f"repos/issues/{number}/sub_issues")
            titles = {item["number"]: item["title"] for item in listed or []} or titles
        change(number)["parts"] += [(n, title) for n, title in titles.items() if n not in said]
        change(number)["depends"] += [n for n in native["depends"] if n not in task_links.depends(node["body"])]
        change(number)["native"] += [n for n in task_links.parts(node["body"]) if n not in native["parts"]]
        change(number)["native"] += [n for n in task_links.depends(node["body"]) if n not in native["depends"]]
        change(number)["label"] = task_links.RETIRED_LABEL in [label["name"] for label in (node.get("labels") or {}).get("nodes", [])]
        parent = native["parent"]
        if parent and parent not in by_number:  # a closed parent: the open part is its line's only reader
            change(parent)["parts"].append((number, issue_state.title(node)))
    for number, found in changes.items():
        if found["scope"] is None:
            record = board.fresh(number, comments=False)
            found["scope"] = next((name for name in (record or {}).get("labels", []) if name.startswith("scope:")), "no scope")
            found["body"] = record["body"] if record else None
            found["parts"] = [(n, title) for n, title in found["parts"] if n not in task_links.parts(found["body"] or "")]
        else:
            found["body"] = by_number[number]["body"]
    return {number: found for number, found in sorted(changes.items()) if found["parts"] or found["depends"] or found["label"] or found["native"]}


def describe(number, found):
    said = []
    said += [f"parts {' '.join(f'#{n}' for n, _ in found['parts'])}"] if found["parts"] else []
    said += [f"depends on {' '.join(f'#{n}' for n in found['depends'])}"] if found["depends"] else []
    said += [f"drop the `{task_links.RETIRED_LABEL}` label"] if found["label"] else []
    said += [f"link {' '.join(f'#{n}' for n in found['native'])} natively"] if found["native"] else []
    return f"#{number} ({found['scope']}{'' if found['open'] else ', closed: the edit opens it'}): " + "; ".join(said)


def apply(number, found):
    """Writes one issue's change; the error line when a write was refused, else None."""
    old = found["body"] or ""
    new = with_parts(old, [f"[task] #{n} {title}" for n, title in found["parts"]]) if found["parts"] else old
    new = with_depends(new, found["depends"]) if found["depends"] else new
    if new != old:
        work = pathlib.Path(tempfile.mkdtemp())
        (work / "old.md").write_text(old)
        (work / "new.md").write_text(new)
        diff = subprocess.run(["/usr/bin/diff", "-u", "old.md", "new.md"], cwd=work, capture_output=True, text=True).stdout
        (work / "body.diff").write_text(diff)
        done = subprocess.run([sys.executable, str(HERE / "edit-issue-body.py"), str(number), str(work / "body.diff"), WHY], capture_output=True, text=True)
        if done.returncode:
            return f"#{number}: {(done.stderr or done.stdout).strip()}"
    elif found["native"]:  # an edit links them itself
        board_github.mirror(number, old, old)
    if found["label"]:
        board.label(number, task_links.RETIRED_LABEL, True)
    return None


def main(args):
    if args not in ([], ["--dry-run"]):
        print(__doc__, file=sys.stderr)
        return 2
    if board.kind() != "github":
        print(f"sync-task-links: the {board.kind()} board keeps no native links, so nothing changes\n0 to change")
        return 0
    nodes = board.tree(None)
    if nodes is None:
        print("sync-task-links: the board read failed, so nothing changed", file=sys.stderr)
        return 1
    changes = plan(nodes)
    for number, found in changes.items():
        print(("would write " if args else "") + describe(number, found))
        refused = None if args else apply(number, found)
        if refused:
            print(f"refused {refused}")
    if not args and changes:
        nodes = board.tree(None)
        changes = plan(nodes) if nodes is not None else changes
    gaps = [gap for gap in task_links.drift(nodes) if not gap.startswith(("native-only", "body-only", "label"))] if args else task_links.drift(nodes)
    for gap in gaps:
        print(f"gap {gap}")
    print(f"{len(changes) + len(gaps) if args else len(gaps)} to change")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
