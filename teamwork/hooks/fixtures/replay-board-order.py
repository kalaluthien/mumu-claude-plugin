#!/usr/bin/env python3
"""Draw a board of four open tasks through list-issue-board.py and print `PASS` as the last line when a held task with an open blocker sorts after a held task with none, else `FAIL: <what differed>` and exit 1.

usage: replay-board-order.py"""
import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_probe  # noqa: E402

LISTER = pathlib.Path(__file__).resolve().parents[1] / "list-issue-board.py"


def node(number, holder, stamp, blocker=None):
    comments = [{"body": f"DECIDED: x\n\n```teamwork\nholders: {holder}\n```" if holder else "x", "createdAt": stamp, "trusted": True}]
    return {"number": number, "title": f"Task {number}", "url": f"u/{number}", "state": "OPEN", "labels": {"nodes": []}, "comments": {"nodes": comments},
            "body": "## Goal\n\nx\n" + (f"\n```teamwork\ndepends on: #{blocker}\n```\n" if blocker else ""), "trusted": True}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    nodes = [node(1, "a-worker", "2026-01-04", blocker=4), node(2, "b-worker", "2026-01-03"), node(3, "", "2026-01-02"), node(4, "", "2026-01-01")]
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "nodes.json"
        path.write_text(json.dumps(nodes))
        done = subprocess.run([sys.executable, str(LISTER), "--nodes", str(path), "--json"], capture_output=True, text=True)
    if done.returncode:
        return replay_probe.fail(f"list-issue-board.py exited {done.returncode}: {done.stderr.strip()[-200:]}")
    order = [row["number"] for row in json.loads(done.stdout)]
    if order != [2, 1, 3, 4]:
        return replay_probe.fail(f"the board lists {order}, not [2, 1, 3, 4]: the held task with an open blocker must sort after the held task with none")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
