#!/usr/bin/env python3
"""Close every stale worker tab of one checkout.

usage: tab-sweep.py <checkout>

A tab is stale when every one of its panes runs no agent `herdr agent list`
names and has its cwd under `<checkout>/.claude/worktrees/`; leads' tabs and
other checkouts' tabs never match. Closes each with `herdr tab close` and
prints its tab id, one per line.
"""
import json
import pathlib
import subprocess
import sys


def herdr(*argv):
    return subprocess.run(["herdr", *argv], capture_output=True, text=True, check=True).stdout


def stale_tabs(panes, agents, checkout):
    """Tab ids whose every pane is agentless and under `checkout`'s worktrees."""
    root = pathlib.Path(checkout) / ".claude" / "worktrees"
    busy = {a["pane_id"] for a in agents}
    tabs = {}
    for p in panes:
        ok = p["pane_id"] not in busy and pathlib.Path(p["cwd"]).is_relative_to(root) and pathlib.Path(p["cwd"]) != root
        tabs[p["tab_id"]] = tabs.get(p["tab_id"], True) and ok
    return [t for t, ok in tabs.items() if ok]


def main(argv):
    if len(argv) != 1:
        print("usage: tab-sweep.py <checkout>", file=sys.stderr)
        return 2
    panes = json.loads(herdr("pane", "list"))["result"]["panes"]
    agents = json.loads(herdr("agent", "list"))["result"]["agents"]
    for tab in stale_tabs(panes, agents, argv[0]):
        herdr("tab", "close", tab)
        print(tab)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
