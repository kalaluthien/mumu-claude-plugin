#!/usr/bin/env python3
"""Check the task graph's links on a board, writing only through use-board.py, and print `ok <case>` or `fail <case>: <what it saw>` per case,
then `PASS` or `FAIL`; exit 1 on any fail. The git board runs every case but the nodes', in a scratch repository whose manager and worker live in a fake herdr,
its heartbeat lines printed by print-team-gaps.py; nodes the link gaps and the pane, from task nodes written here by hand. A record the scripts print no
part of is read by the plugin's lib in a process of the scratch repository's own.
- refuse-cycle, refuse-part-waits-on-parent, refuse-second-parent-open, refuse-second-parent-closed, refuse-unknown: an `edit` or a `depend`
  that exits 1 naming the tasks, the body, the comments and the tasks it waits on unchanged; refuse-on-file: a `file` naming an unknown task exits 1, no task made
- derive-waits, derive-released, derive-not-planned-holds, derive-parent-closes, derive-parent-stays, derive-stopped-part-holds-parent,
  derive-drop-closes-parent, derive-follow-up-reopens, derive-link-edit-keeps-ask (neither a `depend` nor a body edit's `DECIDED:` answers a `BLOCKED:`; a
  decision naming it by `--answers` does), derive-stop-closes-parts
- read-second-parent: a part two bodies name reads the same parent from its record as from the parts list
- heartbeat-cycle, heartbeat-second-parent, heartbeat-backlog-label: the manager's `links` lines;
  heartbeat-tree-unread: a failed tree read leaves the manager's read whole, with one `unread` link line, the read made to fail in process, since the git board's never does
- pane-nesting, pane-wait-line, pane-done-count: list-task-board.py's lines

usage: replay-task-graph.py [--board <git|nodes>]   (no argument: both in turn)"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))
import replay_probe  # noqa: E402

USE = HERE.parent / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
GAPS = ROOT / "monitors" / "print-team-gaps.py"
cases = replay_probe.Cases()


def evaluate(code):
    """The JSON value the last line of CODE prints, run with the plugin's lib in the sandbox's repository and environment."""
    return sandbox.evaluate(f"import json\n{code}")


def value(expression, modules="board"):
    return evaluate(f"import {modules}\nprint(json.dumps({expression}))")


def body(parts=(), check=True):
    """A task's body: a goal, then a Definition of done of a check, when CHECK, and its parts."""
    items = ([replay_probe.CHECK] if check else []) + [f"{i}. [task] #{n} Probe part {n}\n" for i, n in enumerate(parts, 1 + check)]
    return f"## Goal\n\nProbe the task graph.\n\nPath: caller: the probe run; meets: the owner\n\n## Definition of done\n\n{''.join(items)}"


def use(*argv, **options):
    return sandbox.python(USE, *map(str, argv), **options)


def write(name, text):
    return replay_probe.write_text(sandbox.work, name, text)


def file(title, text, depends=()):
    done = use("file", "--title", title, "--body", write("file.md", text), "--depends", " ".join(map(str, depends)))
    if done.returncode:
        raise SystemExit(f"replay-task-graph: cannot file {title}: {done.stderr}")
    return int(done.stdout.strip().rsplit("/", 1)[1])


def edit(number, text):
    """Rewrites NUMBER's body to TEXT through `use-board.py edit`, from the body sha `read` prints."""
    sha = re.search(r"^body sha: (\S+)$", use("read", number).stdout, re.M).group(1)
    return use("edit", number, "--body", write("edit.md", text), "--reason", "probe a link edit", "--base", sha)


def resolve(number, stopped=False):
    return use("resolve", number, "--summary", "probe done", *(["--not-planned"] if stopped else []))


def depend(number, *targets):
    return use("depend", number, "--depends", " ".join(map(str, targets)))


def seen(number):
    return value(f"(lambda record: (record['body'], len(record['comments']), record['depends']))(board.fresh({number}))")


def refused(name, number, call, *named):
    """CALL, an edit or a depend of NUMBER, exits 1, its message naming each of NAMED, and leaves the body, the comments and the tasks it waits on as they were."""
    before = seen(number)
    done = call()
    said = done.stderr + done.stdout
    cases.step(name, done.returncode == 1 and all(f"#{n}" in said for n in named) and seen(number) == before, f"exit {done.returncode}: {said}")


def closed(number):
    return value(f"board.fresh({number}, comments=False)['state']") == "CLOSED"


def refuse_cases():
    first, second = file("Probe first", body()), file("Probe second", body())
    depend(first, second)
    refused("refuse-cycle", second, lambda: edit(second, body(parts=[first])), first, second)
    part = file("Probe a part", body())
    parent = file("Probe a parent", body(parts=[part], check=False))
    refused("refuse-part-waits-on-parent", part, lambda: depend(part, parent), part, parent)
    other = file("Probe another parent", body(check=False))
    refused("refuse-second-parent-open", other, lambda: edit(other, body(parts=[part], check=False)), part, parent)
    closed_part = file("Probe a closed parent's part", body())
    closed_parent = file("Probe a closed parent", body(parts=[closed_part]))
    resolve(closed_parent)
    refused("refuse-second-parent-closed", other, lambda: edit(other, body(parts=[closed_part], check=False)), closed_part, closed_parent)
    unknown = 10 ** 7
    refused("refuse-unknown", first, lambda: depend(first, second, unknown), unknown)
    count = value("len(board.tasks('all', comments=False))")
    done = use("file", "--title", "Probe an unknown link", "--body", write("file.md", body()), "--depends", unknown)
    cases.step("refuse-on-file", done.returncode == 1 and f"#{unknown}" in done.stderr and value("len(board.tasks('all', comments=False))") == count, f"exit {done.returncode}: {done.stderr}")


def derive_cases():
    target, other = file("Probe a target", body()), file("Probe a stopped target", body())
    waiting, holding = file("Probe a waiting task", body(), [target]), file("Probe a held task", body(), [other])
    blockers = lambda number: value(f"board.blockers({number})")
    found = blockers(waiting)
    cases.step("derive-waits", found == [target], found)
    resolve(target)
    found = blockers(waiting)
    cases.step("derive-released", found == [], found)
    resolve(other, stopped=True)
    found = blockers(holding)
    cases.step("derive-not-planned-holds", found == [other], found)

    first, second = file("Probe part one", body()), file("Probe part two", body())
    parent = file("Probe a parent of parts", body(parts=[first, second], check=False))
    resolve(first)
    half = closed(parent)
    resolve(second)
    cases.step("derive-parent-closes", not half and closed(parent), f"after one part closed {half}, after both {closed(parent)}")
    lone = file("Probe a part of a checked parent", body())
    checked = file("Probe a checked parent", body(parts=[lone]))
    resolve(lone)
    cases.step("derive-parent-stays", not closed(checked), "the parent closed")
    stopped, done = file("Probe a stopped part", body()), file("Probe a done part", body())
    holder = file("Probe a parent of a stopped part", body(parts=[stopped, done], check=False))
    resolve(stopped, stopped=True)
    resolve(done)
    cases.step("derive-stopped-part-holds-parent", not closed(holder), "the parent closed")
    edit(holder, body(parts=[done], check=False))
    cases.step("derive-drop-closes-parent", closed(holder), "the parent stayed open once the stopped part's line was dropped")
    follow_up = file("Probe a follow-up", body())
    edit(parent, body(parts=[first, second, follow_up], check=False))
    cases.step("derive-follow-up-reopens", not closed(parent), "the parent stayed closed")

    asking = lambda: value(f"team_gaps.asking(board.fresh({asker}))", "board, team_gaps")
    target, asker = file("Probe a target of an asking task", body()), file("Probe an asking task", body())
    question = use("comment", asker, "--blocked", "which way?", "--text", write("ask.md", "1. one\n2. another\n")).stdout.strip()
    depend(asker, target)
    linked = asking()
    edit(asker, body().replace("prints `ok`", "prints `ok` once"))
    edited = asking()
    use("decide", asker, "--decision", "one", "--answers", question, claude=["--name", "probe-manager"])
    answered = asking()
    cases.step("derive-link-edit-keeps-ask", linked and edited and not answered, f"asking after the link {linked}, the criterion edit {edited}, the answer {answered}")

    parts = [file("Probe a part to stop", body()), file("Probe another part to stop", body())]
    stop = file("Probe a parent to stop", body(parts=parts, check=False))
    resolve(stop, stopped=True)
    records = value(f"[dict(record, completed=task_links.completed(record)) for record in (board.fresh(n, comments=False) for n in {parts})]", "board, task_links")
    decided = [comment["body"] for comment in value(f"board.fresh({stop})['comments']") if comment["body"].startswith("DECIDED:")]
    cases.step("derive-stop-closes-parts", all(record["state"] == "CLOSED" and not record["completed"] for record in records)
         and len(decided) == 1 and all(f"#{n}" in decided[0] for n in parts), f"{[(record['state'], record.get('stateReason') or record.get('reason')) for record in records]} {decided}")


def heartbeat_cases(lines):
    """The cases on LINES, the manager's `links` lines."""
    has = lambda pattern: any(re.search(pattern, line) for line in lines)
    cases.step("heartbeat-cycle", has(r"^links cycle #(\d+) → #(\d+) → #\1"), lines)
    cases.step("heartbeat-second-parent", has(r"^links second parent #\d+: #\d+ and #\d+"), lines)
    cases.step("heartbeat-backlog-label", has(r"^links label #\d+: .*`backlog`"), lines)


def heartbeat():
    """The `links` lines print-team-gaps.py prints in one poll as the manager."""
    done = sandbox.python(GAPS, "--polls", "1", pane="w1:p1")
    return [line for line in done.stdout.splitlines() if line.startswith("links ")] or [f"exit {done.returncode}: {done.stdout}{done.stderr}"]


def heartbeat_unread():
    """The manager's read with the tree read failing, as a failed read gives it; the pull requests stand in as none."""
    links = evaluate("""import board, landing, team_gaps
board.tree, landing.pulls = (lambda *args, **kwargs: None), (lambda *args, **kwargs: [])
data = team_gaps.manager_read({"name": "probe-manager", "workspace_id": ""})
print(json.dumps(data and data["links"]))""")
    cases.step("heartbeat-tree-unread", links is not None and [gap.split(":")[0] for gap in links] == ["unread"], links)


def git_drift():
    """Writes, behind the write path, the drift two concurrent writes can leave: a cycle and a part two parents name; and the retired label."""
    first, second, part = file("Probe a drift", body()), file("Probe a drift's pair", body()), file("Probe a doubly claimed part", body())
    one, two = file("Probe one claimant", body(check=False)), file("Probe another claimant", body(check=False))
    parent, owner = evaluate(f"""import board_git, board_records
store = board_git.STORE
store.write(lambda: [board_records.save(store, number, depends=[other]) for number, other in (({first}, {second}), ({second}, {first}))]
            + [store.stage(f"{{board_records.home(store, number)}}/body.md", {body(parts=[part], check=False)!r}) for number in ({one}, {two})])
store.refresh()
print(json.dumps((board_records.record(store, {part}, comments=False)["parent"], board_records.owners(store).get({part}))))""")
    cases.step("read-second-parent", parent == owner is not None, (parent, owner))
    use("label", first, "--label", "backlog")


def node(number, text, labels=(), state="OPEN", reason=None, depends=None):
    return {**({} if depends is None else {"depends": depends}), "number": number, "title": f"Probe {number}", "url": f"https://github.com/o/r/issues/{number}", "body": text, "authorAssociation": "OWNER",
            "state": state, "stateReason": reason, "parent": None, "labels": {"nodes": [{"name": name} for name in labels]},
            "parts": {"nodes": []}, "partsSummary": {"total": 0}, "blockedBy": {"nodes": []}, "comments": {"nodes": []}}


def pane_nodes():
    """A root whose parts are a closed task and one waiting on two open tasks."""
    return [node(1, body(parts=[2, 3], check=False)), node(2, body(), state="CLOSED", reason="COMPLETED"), node(3, body(), depends=[4, 5]),
            node(4, body()), node(5, body())]


def drift_nodes():
    return [node(1, body(), labels=["backlog"], depends=[2]), node(2, body(), depends=[1]),
            node(3, body()), node(4, body(parts=[3], check=False)), node(5, body(parts=[3], check=False))]


def pane_cases(lines, root, waiting, first, second):
    rows = [line for line in lines if re.match(r"^[\s│├└]*#\d+ ", line)]
    under = [line for line in rows if line.lstrip(" │├└").startswith(f"#{waiting} ")]
    cases.step("pane-nesting", len(under) == 1 and under[0].startswith(("  └ ", "  ├ ")) and rows[0].startswith(f"#{root} "), rows)
    cases.step("pane-wait-line", sum(line.endswith(f"(blocked by #{first} #{second})") for line in lines) == 1, lines)
    cases.step("pane-done-count", any(line.strip(" │").startswith("1/2 parts done") for line in lines), lines)


def main(args):
    global sandbox
    if not args:
        return replay_probe.run_every(__file__, "--board", ("git", "nodes"))
    if len(args) != 2 or args[0] != "--board" or args[1] not in ("git", "nodes"):
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("task-graph-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("probe-manager", 1), replay_probe.agent("probe-worker", 2)])
        if args[1] == "nodes":
            nodes()
        else:
            git()
    return cases.finish()


def nodes():
    gaps = value(f"task_links.drift(board.tree(None, {drift_nodes()!r}))", "board, task_links")
    heartbeat_cases([f"links {gap}" for gap in gaps])
    shown = sandbox.python(LIST, "--nodes", write("nodes.json", json.dumps(pane_nodes())))
    pane_cases(shown.stdout.splitlines(), 1, 3, 4, 5)


def git():
    refuse_cases()
    derive_cases()
    git_drift()
    heartbeat_cases(heartbeat())
    heartbeat_unread()
    first, second, closed_part = file("Probe a first target", body()), file("Probe a second target", body()), file("Probe a done part", body())
    waiting = file("Probe a part that waits", body(), [first, second])
    root = file("Probe a pane root", body(parts=[closed_part, waiting], check=False))
    resolve(closed_part)
    lines = sandbox.python(LIST, "probe").stdout.splitlines()
    # the board holds every case's tasks, so only the root's block is read: from its row to the next root's
    start = next((i for i, line in enumerate(lines) if line.startswith(f"#{root} ")), len(lines))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#\d+ ", lines[i])), len(lines))
    pane_cases(lines[start:end], root, waiting, first, second)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
