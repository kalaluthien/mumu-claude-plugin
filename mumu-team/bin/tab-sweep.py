#!/usr/bin/env python3
"""Close every stale worker tab of one checkout.

usage: tab-sweep.py <checkout>

A tab is stale when every one of its panes runs no agent `herdr agent list`
names and has its cwd in a worktree of `<checkout>` (`lib/names.py`); leads' tabs and
other checkouts' tabs never match. Closes each with `herdr tab close` and
prints its tab id, one per line.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import herdr  # noqa: E402
import names  # noqa: E402


def stale_tabs(panes, agents, checkout):
    """Tab ids whose every pane is agentless and under `checkout`'s worktrees."""
    root = names.worktrees(checkout)
    busy = {a["pane_id"] for a in agents}
    tabs = {}
    for p in panes:
        ok = p["pane_id"] not in busy and (cwd := pathlib.Path(p["cwd"]).resolve()).is_relative_to(root) and cwd != root
        tabs[p["tab_id"]] = tabs.get(p["tab_id"], True) and ok
    return [t for t, ok in tabs.items() if ok]


def main(argv):
    if len(argv) != 1:
        print("usage: tab-sweep.py <checkout>", file=sys.stderr)
        return 2
    try:
        for tab in stale_tabs(herdr.panes(), herdr.agents(), argv[0]):
            herdr.close_tab(tab)
            print(tab)
    except RuntimeError as e:
        print(f"tab-sweep.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
