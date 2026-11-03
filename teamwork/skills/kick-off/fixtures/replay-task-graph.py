#!/usr/bin/env python3
"""Check the task graph's links on a board, writing only through use-board.py, and print `ok <case>` or `fail <case>: <what it saw>` per case;
exit 1 on any fail. The boards run the cases they can: files and git every case but the mirror's, the heartbeat's on files only, since it writes
a body behind the write path; github the refusals, the derived state and the mirror, on the repository `GH_REPO` names, as the tape of
recorded-gh/gh beside this file holds it, never this one, since its issues would reach the team's board; github-nodes the heartbeat and the
pane, from GitHub-shaped nodes written here by hand.
- refuse-cycle, refuse-part-waits-on-parent, refuse-second-parent-open, refuse-second-parent-closed, refuse-unknown, refuse-too-many: an `edit`
  that exits 1 naming the issues, the body and comments unchanged; refuse-on-file: a `file` naming an unknown issue exits 1, no issue made
- derive-waits, derive-released, derive-not-planned-holds, derive-parent-closes, derive-parent-stays, derive-stopped-part-holds-parent,
  derive-drop-closes-parent, derive-follow-up-reopens, derive-stop-closes-parts
- mirror-file, mirror-edit: GitHub's native sub-issue and `blocked by` links follow the body
- refuse-pull-request, derive-tree-names-no-issue, on github only: an edit naming a pull request exits 1; a body naming a pull request and
  a missing issue, written behind the write path, leaves the tree read whole
- heartbeat-cycle, heartbeat-second-parent, heartbeat-backlog-label, and on github-nodes heartbeat-native-only and heartbeat-body-only
- pane-nesting, pane-wait-line, pane-done-count, pane-named-no-row: list-issue-board.py's lines, with no native link written, and no
  row for an issue outside the scope that only a body names

usage: replay-task-graph.py --board <files|git|github|github-nodes>"""
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
THIS_REPO = "kalaluthien/mumu-claude-plugin"
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
    return use("edit", number, write("edit.diff", diff), "DECIDED: probe a link edit")


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
    many_depends, many_parts = edit(first, body(depends=range(unknown, unknown + 51))), edit(first, body(parts=range(unknown, unknown + 101)))
    said = many_depends.stderr + many_parts.stderr
    step("refuse-too-many", many_depends.returncode == 1 and many_parts.returncode == 1 and "51 `depends on`" in said and "101 parts" in said
         and seen(first)[0] == body(depends=[second]), said)
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

    parts = [file("Probe a part to stop", body()), file("Probe another part to stop", body())]
    stop = file("Probe a parent to stop", body(parts=parts, check=False))
    resolve(stop, stopped=True)
    records = [board.fresh(n, comments=False) for n in parts]
    decided = [comment["body"] for comment in board.fresh(stop)["comments"] if comment["body"].startswith("DECIDED:")]
    step("derive-stop-closes-parts", all(record["state"] == "CLOSED" and not task_links.completed(record) for record in records)
         and len(decided) == 1 and all(f"#{n}" in decided[0] for n in parts), f"{[(r['state'], r.get('stateReason') or r.get('reason')) for r in records]} {decided}")


def mirror_cases():
    import board_github
    native = lambda n: (sorted(item["number"] for item in board_github.get(f"repos/issues/{n}/sub_issues") or []),
                        sorted(item["number"] for item in board_github.get(f"repos/issues/{n}/dependencies/blocked_by") or []))
    target, part = file("Probe a mirrored target", body()), file("Probe a mirrored part", body())
    linked = file("Probe a mirrored task", body(depends=[target], parts=[part]))
    step("mirror-file", native(linked) == ([part], [target]), native(linked))
    new_target, new_part = file("Probe a new mirrored target", body()), file("Probe a new mirrored part", body())
    edit(linked, body(depends=[new_target], parts=[new_part]))
    step("mirror-edit", native(linked) == ([new_part], [new_target]), native(linked))


def not_issue_cases():
    import board_github
    pulls = board_github.get("repos/pulls?state=all&per_page=1", paginate=False) or [{"number": 0}]
    pull, task = pulls[0]["number"], file("Probe a link to a pull request", body())
    refused("refuse-pull-request", task, body(depends=[pull]), pull)
    # written behind the write path, as a body written before the refusal existed may name them
    board_github.write("-X", "PATCH", f"repos/{{owner}}/{{repo}}/issues/{task}", "-F", "body=@-", text=body(depends=[pull, 10 ** 7]))
    nodes = board.tree(None)
    step("derive-tree-names-no-issue", nodes is not None and task in [node["number"] for node in nodes], "the tree read failed" if nodes is None else f"#{task} missing")


def heartbeat(nodes):
    """The heartbeat's link lines for NODES, a board's tree."""
    import task_links as links
    import team_gaps
    team_gaps.tabs, team_gaps.crowding, team_gaps.members = (lambda workspace: []), (lambda me, listed: []), (lambda me, listed: [])
    data = {"found": [], "everything": [], "prs": [], "outside": [], "feed": [], "links": links.drift(nodes)}
    return [line for line in team_gaps.manager_actions({"name": "probe-manager", "workspace_id": ""}, [], data) if line.startswith("links ")]


def heartbeat_cases(nodes, native):
    lines = heartbeat(nodes)
    has = lambda pattern: any(re.search(pattern, line) for line in lines)
    step("heartbeat-cycle", has(r"^links cycle #(\d+) → #(\d+) → #\1"), lines)
    step("heartbeat-second-parent", has(r"^links second parent #\d+: #\d+ and #\d+"), lines)
    step("heartbeat-backlog-label", has(r"^links label #\d+: .*`backlog`"), lines)
    if native:
        step("heartbeat-native-only", has(r"^links native-only #\d+: GitHub links #\d+"), lines)
        step("heartbeat-body-only", has(r"^links body-only #\d+: its body names #\d+"), lines)


def files_drift():
    """Writes, behind the write path, the drift two concurrent writes can leave: a cycle and a part two parents name; and the retired label."""
    first, second, part = file("Probe a drift", body()), file("Probe a drift's pair", body()), file("Probe a doubly claimed part", body())
    one, two = file("Probe one claimant", body(check=False)), file("Probe another claimant", body(check=False))
    folder = pathlib.Path(os.environ["TEAMWORK_BOARD_DIR"])
    for number, text in ((first, body(depends=[second])), (second, body(depends=[first])), (one, body(parts=[part], check=False)), (two, body(parts=[part], check=False))):
        (folder / str(number) / "body.md").write_text(text)
    use("label", first, "backlog")
    return board.tree(None)


def node(number, text, labels=(), native_parts=(), native_depends=(), state="OPEN", reason=None):
    return {"number": number, "title": f"Probe {number}", "url": f"https://github.com/o/r/issues/{number}", "body": text, "authorAssociation": "OWNER",
            "state": state, "stateReason": reason, "parent": None, "labels": {"nodes": [{"name": name} for name in labels]},
            "subIssues": {"nodes": [{"number": n, "title": f"Probe {n}"} for n in native_parts]}, "subIssuesSummary": {"total": len(native_parts)},
            "blockedBy": {"nodes": [{"number": n} for n in native_depends]}, "comments": {"nodes": []}}


def pane_nodes():
    """A root whose parts are a closed task and one waiting on two open tasks, as GitHub's read gives them with no native link; one of
    those waits on an open issue outside the scope, which only its body names."""
    return [node(1, body(parts=[2, 3], check=False)), node(2, body(), state="CLOSED", reason="COMPLETED"), node(3, body(depends=[4, 5])),
            node(4, body(depends=[6])), node(5, body()), {**node(6, body()), "named": True}]


def drift_nodes():
    return [node(1, body(depends=[2]), labels=["backlog"], native_depends=[2]), node(2, body(depends=[1]), native_depends=[1]),
            node(3, body()), node(4, body(parts=[3], check=False), native_parts=[3]), node(5, body(parts=[3], check=False), native_parts=[3]),
            node(6, body(), native_parts=[3]), node(7, body(depends=[3]))]


def pane_cases(lines, root, waiting, first, second, named=None):
    rows = [line for line in lines if re.match(r"^[\s│├└]*#\d+ ", line)]
    under = [line for line in rows if line.lstrip(" │├└").startswith(f"#{waiting} ")]
    step("pane-nesting", len(under) == 1 and under[0].startswith(("  └ ", "  ├ ")) and rows[0].startswith(f"#{root} "), rows)
    step("pane-wait-line", sum(line.strip(" │") == f"← #{first} #{second}" for line in lines) == 1, lines)
    step("pane-done-count", any(line.strip(" │").startswith("1/2 done") for line in lines), lines)
    if named:
        step("pane-named-no-row", not any(line.lstrip(" │├└").startswith(f"#{named} ") for line in rows), rows)


def main(args):
    global work, board, task_links
    if len(args) != 2 or args[0] != "--board" or args[1] not in ("files", "git", "github", "github-nodes"):
        print(__doc__, file=sys.stderr)
        return 2
    kind = args[1]
    work = pathlib.Path(tempfile.mkdtemp(prefix="task-graph-"))
    os.environ["TEAMWORK_BOARD"] = "github" if kind.startswith("github") else kind
    if kind != "github":  # gh signs in from HOME, and the tape sits in the Claude config folder
        os.environ.update({"HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "config")})
    if kind == "github" and (os.environ.get("GH_REPO") or THIS_REPO) == THIS_REPO:
        sys.exit("replay-task-graph: not a sandbox: set GH_REPO to a repository whose issues the team's board never reads")
    if kind == "files":
        os.environ["TEAMWORK_BOARD_DIR"] = str(work / "board")
    elif kind == "git":
        subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
        os.chdir(work / "repo")
    elif kind == "github":
        os.environ.update({"PATH": f"{HERE / 'recorded-gh'}:{os.environ['PATH']}", "GH_TAPE": "replay-task-graph", "GH_TAPE_STATE": str(work / "gh-turns.json")})
    sys.path.insert(0, str(ROOT / "lib"))
    # imported here, since they read the board set above when they load
    import board
    import task_links

    if kind == "github-nodes":
        (work / "nodes.json").write_text(json.dumps(drift_nodes()))
        heartbeat_cases(board.tree(None, json.loads((work / "nodes.json").read_text())), native=True)
        (work / "nodes.json").write_text(json.dumps(pane_nodes()))
        shown = subprocess.run([sys.executable, str(LIST), "--nodes", str(work / "nodes.json")], capture_output=True, text=True)
        pane_cases(shown.stdout.splitlines(), 1, 3, 4, 5, named=6)
        return 1 if failures else 0
    refuse_cases()
    derive_cases()
    if kind == "github":
        mirror_cases()
        not_issue_cases()
        return 1 if failures else 0
    if kind == "files":
        heartbeat_cases(files_drift(), native=False)
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
