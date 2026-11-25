#!/usr/bin/env python3
"""Draw a board of four open tasks through list-task-board.py, as a session whose herdr lists both holders, and print `PASS` as the last line when a held task with an open
blocker sorts after a held task with none, else `FAIL: <what differed>` and exit 1.

usage: replay-board-order.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

LISTER = pathlib.Path(__file__).resolve().parents[1] / "list-task-board.py"


def node(number, holder, stamp, blocker=None):
    """A task record as a nodes file holds it, the board's tasks before their links are read: what it waits on is its `depends`."""
    comments = [{"body": "DECIDED: x" if holder else "x", "fields": {"holders": [holder]} if holder else {}, "createdAt": stamp, "trusted": True}]
    return {"number": number, "title": f"Task {number}", "url": f"u/{number}", "state": "OPEN", "labels": {"nodes": []}, "comments": {"nodes": comments},
            "body": "## Goal\n\nx\n", "depends": [blocker] if blocker else [], "trusted": True}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    nodes = [node(1, "a-worker", "2026-01-04", blocker=4), node(2, "b-worker", "2026-01-03"), node(3, "", "2026-01-02"), node(4, "", "2026-01-01")]
    with replay_probe.scratch("board-order-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("a-worker", 2), replay_probe.agent("b-worker", 3)])
        done = sandbox.python(LISTER, "--nodes", replay_probe.write_text(work, "nodes.json", json.dumps(nodes)), "--json")
    if done.returncode:
        return replay_probe.fail(f"list-task-board.py exited {done.returncode}: {done.stderr.strip()[-200:]}")
    order = [row["number"] for row in json.loads(done.stdout)]
    if order != [2, 1, 3, 4]:
        return replay_probe.fail(f"the board lists {order}, not [2, 1, 3, 4]: the held task with an open blocker must sort after the held task with none")
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
