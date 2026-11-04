#!/usr/bin/env python3
"""Check the task graph's links on a board, writing only through use-board.py, and print `ok <case>` or `fail <case>: <what it saw>` per case;
exit 1 on any fail. The git board runs every case but the nodes'; nodes the heartbeat and the pane, from issue nodes written here by hand.
- refuse-cycle, refuse-part-waits-on-parent, refuse-second-parent-open, refuse-second-parent-closed, refuse-unknown: an `edit`
  that exits 1 naming the issues, the body and comments unchanged; refuse-on-file: a `file` naming an unknown issue exits 1, no issue made
- derive-waits, derive-released, derive-not-planned-holds, derive-parent-closes, derive-parent-stays, derive-stopped-part-holds-parent,
  derive-drop-closes-parent, derive-follow-up-reopens, derive-link-edit-keeps-ask (no body edit's `DECIDED:` answers a `BLOCKED:`; a
  decision naming it in `answers:` does), derive-stop-closes-parts
- heartbeat-cycle, heartbeat-second-parent, heartbeat-backlog-label, 
  heartbeat-tree-unread: a failed tree read leaves the manager's read whole, with one `unread` link line
- pane-nesting, pane-wait-line, pane-done-count: list-issue-board.py's lines

usage: replay-task-graph.py --board <git|nodes>"""
import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
USE = HERE.parent / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
CHECK = "1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
failures = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:400]}", flush=True)
    if not ok:
        failures.append(name)


def body(depends=(), parts=(), check=True):
    """A task's body: a goal, its `depends on` line, then a Definition of done of a check, when CHECK, and its parts."""
    fence = f"```teamwork\ndepends on: {' '.join(f'#{n}' for n in depends)}\n```\n\n" if depends else ""
    items = ([CHECK] if check else []) + [f"{i}. [task] #{n} Probe part {n}\n" for i, n in enumerate(parts, 1 + check)]
    return f"## Goal\n\nProbe the task graph.\n\n{fence}## Definition of done\n\n{''.join(items)}"


def use(*argv):
    return subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True)


def write(name, text):
    path = work / name
    path.write_text(text)
    return path


def file(title, text):
    done = use("file", title, write("file.md", text))
    if done.returncode:
        raise SystemExit(f"replay-task-graph: cannot file {title}: {done.stderr}")
    return int(done.stdout.strip().rsplit("/", 1)[1])


def edit(number, text):
    """Rewrites NUMBER's body to TEXT through `use-board.py edit`."""
    old = board.body(number)
    diff = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), "a", "b"))
    return use("edit", number, write("edit.diff", diff), "DECIDED: probe a link edit", "--base", board.body_sha(old))


def resolve(number, stopped=False):
    return use("resolve", number, write("done.md", "REPORTED: probe done\n"), *(["--not-planned"] if stopped else []))


def seen(number):
    record = board.fresh(number)
    return record["body"], len(record["comments"])


def refused(name, number, text, *named):
    """An edit of NUMBER to TEXT exits 1, its message naming each of NAMED, and leaves the body and comments as they were."""
    before = seen(number)
    done = edit(number, text)
    said = done.stderr + done.stdout
    step(name, done.returncode == 1 and all(f"#{n}" in said for n in named) and seen(number) == before, f"exit {done.returncode}: {said}")


def closed(number):
    return board.fresh(number, comments=False)["state"] == "CLOSED"


def refuse_cases():
    first, second = file("Probe first", body()), file("Probe second", body())
    edit(first, body(depends=[second]))
    refused("refuse-cycle", second, body(parts=[first]), first, second)
    part = file("Probe a part", body())
    parent = file("Probe a parent", body(parts=[part], check=False))
    refused("refuse-part-waits-on-parent", part, body(depends=[parent]), part, parent)
    other = file("Probe another parent", body(check=False))
    refused("refuse-second-parent-open", other, body(parts=[part], check=False), part, parent)
    closed_part = file("Probe a closed parent's part", body())
    closed_parent = file("Probe a closed parent", body(parts=[closed_part]))
    resolve(closed_parent)
    refused("refuse-second-parent-closed", other, body(parts=[closed_part], check=False), closed_part, closed_parent)
    unknown = 10 ** 7
    refused("refuse-unknown", first, body(depends=[second, unknown]), unknown)
    count = len(board.issues("all", comments=False))
    done = use("file", "Probe an unknown link", write("file.md", body(depends=[unknown])))
    step("refuse-on-file", done.returncode == 1 and f"#{unknown}" in done.stderr and len(board.issues("all", comments=False)) == count, f"exit {done.returncode}: {done.stderr}")


def derive_cases():
    target, other = file("Probe a target", body()), file("Probe a stopped target", body())
    waiting, holding = file("Probe a waiting task", body(depends=[target])), file("Probe a held task", body(depends=[other]))
    step("derive-waits", board.blockers(waiting) == [target], board.blockers(waiting))
    resolve(target)
    step("derive-released", board.blockers(waiting) == [], board.blockers(waiting))
    resolve(other, stopped=True)
    step("derive-not-planned-holds", board.blockers(holding) == [other], board.blockers(holding))

    first, second = file("Probe part one", body()), file("Probe part two", body())
    parent = file("Probe a parent of parts", body(parts=[first, second], check=False))
    resolve(first)
    half = closed(parent)
    resolve(second)
    step("derive-parent-closes", not half and closed(parent), f"after one part closed {half}, after both {closed(parent)}")
    lone = file("Probe a part of a checked parent", body())
    checked = file("Probe a checked parent", body(parts=[lone]))
    resolve(lone)
    step("derive-parent-stays", not closed(checked), "the parent closed")
    stopped, done = file("Probe a stopped part", body()), file("Probe a done part", body())
    holder = file("Probe a parent of a stopped part", body(parts=[stopped, done], check=False))
    resolve(stopped, stopped=True)
    resolve(done)
    step("derive-stopped-part-holds-parent", not closed(holder), "the parent closed")
    edit(holder, body(parts=[done], check=False))
    step("derive-drop-closes-parent", closed(holder), "the parent stayed open once the stopped part's line was dropped")
    follow_up = file("Probe a follow-up", body())
    edit(parent, body(parts=[first, second, follow_up], check=False))
    step("derive-follow-up-reopens", not closed(parent), "the parent stayed closed")

    import team_gaps
    target, asker = file("Probe a target of an asking task", body()), file("Probe an asking task", body())
    question = use("comment", asker, write("ask.md", "BLOCKED: which way?\n\n1. one\n2. another\n")).stdout.strip()
    edit(asker, body(depends=[target]))
    linked = team_gaps.asking(board.fresh(asker))
    edit(asker, body(depends=[target]).replace("prints `ok`", "prints `ok` once"))
    edited = team_gaps.asking(board.fresh(asker))
    use("decide", asker, write("answer.md", f"DECIDED: one\n\n```decision\ndecision: one\ndecided by: probe-manager\ndoor: two-way\nanswers: {question}\n```\n"))
    answered = team_gaps.asking(board.fresh(asker))
    step("derive-link-edit-keeps-ask", linked and edited and not answered, f"asking after the link edit {linked}, the criterion edit {edited}, the answer {answered}")

    parts = [file("Probe a part to stop", body()), file("Probe another part to stop", body())]
    stop = file("Probe a parent to stop", body(parts=parts, check=False))
    resolve(stop, stopped=True)
    records = [board.fresh(n, comments=False) for n in parts]
    decided = [comment["body"] for comment in board.fresh(stop)["comments"] if comment["body"].startswith("DECIDED:")]
    step("derive-stop-closes-parts", all(record["state"] == "CLOSED" and not task_links.completed(record) for record in records)
         and len(decided) == 1 and all(f"#{n}" in decided[0] for n in parts), f"{[(r['state'], r.get('stateReason') or r.get('reason')) for r in records]} {decided}")


def heartbeat(nodes):
    """The heartbeat's link lines for NODES, a board's tree."""
    import task_links as links
    import team_gaps
    team_gaps.tabs, team_gaps.crowding, team_gaps.members = (lambda workspace: []), (lambda me, listed: []), (lambda me, listed: [])
    data = {"found": [], "everything": [], "prs": [], "outside": [], "feed": [], "links": links.drift(nodes)}
    return [line for line in team_gaps.manager_actions({"name": "probe-manager", "workspace_id": ""}, [], data) if line.startswith("links ")]


def heartbeat_cases(nodes):
    lines = heartbeat(nodes)
    has = lambda pattern: any(re.search(pattern, line) for line in lines)
    step("heartbeat-cycle", has(r"^links cycle #(\d+) → #(\d+) → #\1"), lines)
    step("heartbeat-second-parent", has(r"^links second parent #\d+: #\d+ and #\d+"), lines)
    step("heartbeat-backlog-label", has(r"^links label #\d+: .*`backlog`"), lines)


def heartbeat_unread():
    """The manager's read with the tree read failing, as a failed read gives it; the
    pull requests stand in as none."""
    import landing
    import team_gaps
    kept = board.tree, landing.pulls
    board.tree, landing.pulls = (lambda *args, **kwargs: None), (lambda *args, **kwargs: [])
    try:
        data = team_gaps.manager_read({"name": "probe-manager", "workspace_id": ""})
    finally:
        board.tree, landing.pulls = kept
    step("heartbeat-tree-unread", data is not None and [gap.split(":")[0] for gap in data["links"]] == ["unread"], data and data["links"])


def git_drift():
    """Writes, behind the write path, the drift two concurrent writes can leave: a cycle and a part two parents name; and the retired label."""
    first, second, part = file("Probe a drift", body()), file("Probe a drift's pair", body()), file("Probe a doubly claimed part", body())
    one, two = file("Probe one claimant", body(check=False)), file("Probe another claimant", body(check=False))
    import board_git
    import board_records
    store = board_git.STORE
    store.write(lambda: [store.stage(f"{board_records.home(store, number)}/body.md", text)
                         for number, text in ((first, body(depends=[second])), (second, body(depends=[first])), (one, body(parts=[part], check=False)), (two, body(parts=[part], check=False)))])
    use("label", first, "backlog")
    return board.tree(None)


def node(number, text, labels=(), state="OPEN", reason=None):
    return {"number": number, "title": f"Probe {number}", "url": f"https://github.com/o/r/issues/{number}", "body": text, "authorAssociation": "OWNER",
            "state": state, "stateReason": reason, "parent": None, "labels": {"nodes": [{"name": name} for name in labels]},
            "subIssues": {"nodes": []}, "subIssuesSummary": {"total": 0}, "blockedBy": {"nodes": []}, "comments": {"nodes": []}}


def pane_nodes():
    """A root whose parts are a closed task and one waiting on two open tasks."""
    return [node(1, body(parts=[2, 3], check=False)), node(2, body(), state="CLOSED", reason="COMPLETED"), node(3, body(depends=[4, 5])),
            node(4, body()), node(5, body())]


def drift_nodes():
    return [node(1, body(depends=[2]), labels=["backlog"]), node(2, body(depends=[1])),
            node(3, body()), node(4, body(parts=[3], check=False)), node(5, body(parts=[3], check=False))]


def pane_cases(lines, root, waiting, first, second):
    rows = [line for line in lines if re.match(r"^[\s│├└]*#\d+ ", line)]
    under = [line for line in rows if line.lstrip(" │├└").startswith(f"#{waiting} ")]
    step("pane-nesting", len(under) == 1 and under[0].startswith(("  └ ", "  ├ ")) and rows[0].startswith(f"#{root} "), rows)
    step("pane-wait-line", sum(line.endswith(f"(blocked by #{first} #{second})") for line in lines) == 1, lines)
    step("pane-done-count", any(line.strip(" │").startswith("1/2 parts done") for line in lines), lines)


def main(args):
    global work, board, task_links
    if len(args) != 2 or args[0] != "--board" or args[1] not in ("git", "nodes"):
        print(__doc__, file=sys.stderr)
        return 2
    kind = args[1]
    work = pathlib.Path(tempfile.mkdtemp(prefix="task-graph-"))
    os.environ.update({"HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "config")})
    subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
    os.chdir(work / "repo")
    sys.path.insert(0, str(ROOT / "lib"))
    # imported here, since they read the repository set above when they load
    import board
    import task_links

    if kind == "nodes":
        (work / "nodes.json").write_text(json.dumps(drift_nodes()))
        heartbeat_cases(board.tree(None, json.loads((work / "nodes.json").read_text())))
        (work / "nodes.json").write_text(json.dumps(pane_nodes()))
        shown = subprocess.run([sys.executable, str(LIST), "--nodes", str(work / "nodes.json")], capture_output=True, text=True)
        pane_cases(shown.stdout.splitlines(), 1, 3, 4, 5)
        return 1 if failures else 0
    refuse_cases()
    derive_cases()
    heartbeat_cases(git_drift())
    heartbeat_unread()
    first, second, closed_part = file("Probe a first target", body()), file("Probe a second target", body()), file("Probe a done part", body())
    waiting = file("Probe a part that waits", body(depends=[first, second]))
    root = file("Probe a pane root", body(parts=[closed_part, waiting], check=False))
    resolve(closed_part)
    shown = subprocess.run([sys.executable, str(LIST), "probe"], capture_output=True, text=True)
    lines = shown.stdout.splitlines()
    # the board holds every case's issues, so only the root's block is read: from its row to the next root's
    start = next((i for i, line in enumerate(lines) if line.startswith(f"#{root} ")), len(lines))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#\d+ ", lines[i])), len(lines))
    pane_cases(lines[start:end], root, waiting, first, second)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
