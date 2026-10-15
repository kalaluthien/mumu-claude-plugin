#!/usr/bin/env python3
"""Prints one line per named live agent: name, pane id, workspace id, status; an unnamed session has no name key, so it is skipped."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import herdr_agents  # noqa: E402

listed, _ = herdr_agents.sessions()
for a in listed:
    if a.get("name"):
        print(a["name"], a.get("pane_id", "-"), a.get("workspace_id", "-"), a.get("agent_status", "-"))
if not listed:
    print("list-agents.py: herdr lists no agent; run it inside herdr.")
