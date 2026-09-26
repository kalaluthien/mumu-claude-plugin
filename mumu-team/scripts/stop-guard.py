#!/usr/bin/env python3
"""Stop hook: refuse a lead's stop while it holds an open root task, a `<folder>-lead` only `scope:<folder>`'s, and no `team-watch` descends from `$CLAUDE_PID`."""
import json
import os
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent / "lib"))
import gh  # noqa: E402
import herdr  # noqa: E402


def watching(root):
    """Whether a `team-watch.py` process descends from pid `root`."""
    rows = [line.split(None, 2) for line in gh.run("ps", "-axo", "pid=,ppid=,command=").splitlines()]
    parent = {int(r[0]): int(r[1]) for r in rows}
    for pid in (int(r[0]) for r in rows if len(r) > 2 and "/team-watch.py" in r[2]):
        seen = set()
        while pid in parent and pid not in seen and pid != root:
            seen.add(pid)
            pid = parent[pid]
        if pid == root:
            return True
    return False


payload = json.load(sys.stdin)
cwd = payload.get("cwd") or "."
try:  # a `<folder>-lead`, its folder in `cwd`, holds only `scope:<folder>`'s
    folder = (herdr.agent(os.environ.get("HERDR_PANE_ID"), "pane_id") or {}).get("name", "").removesuffix("-lead")
except RuntimeError:
    folder = ""
held = payload.get("agent_type") == "mumu-team:lead" and gh.held(cwd, folder if folder and (pathlib.Path(cwd) / folder).is_dir() else None)
if held and not watching(int(os.environ.get("CLAUDE_PID") or os.getppid())):
    print(json.dumps({"decision": "block", "reason": f"You hold open root tasks ({' '.join(held)}) and `team-watch` is not running: arm "
                      f"`\"{SCRIPTS / 'team-watch.py'}\"` with the Monitor tool at its longest timeout, in your checkout, before you stop."}))
