"""What `stop.py` and `team-watch.py` read: a lead's open root goals on GitHub and its workers in herdr.

A lead is the one session of its checkout (its cwd); its workers are the herdr
agents named `<topic>-<n>-<k>` whose cwd lies in `<checkout>/.claude/worktrees/`.
"""
import json
import pathlib
import re
import subprocess

WORKER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*-(\d+)-(\d+)")
ROOT_GOALS = ["issue", "list", "--label", "kind:goal", "--state", "open", "--search", "no:parent-issue", "--json", "url"]


def root_goals(cwd):
    """The urls of the open root goals of `cwd`'s repository, or None when `gh` cannot read them."""
    try:
        run = subprocess.run(["gh", *ROOT_GOALS], cwd=cwd, capture_output=True, text=True)
        return [i["url"] for i in json.loads(run.stdout)] if run.returncode == 0 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def agents():
    """herdr's agents, or None when `herdr agent list` cannot be run or read."""
    try:
        return json.loads(subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True).stdout)["result"]["agents"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def workers(listed, checkout):
    """`{name: agent_status}` of the agents in `listed` that are workers of the lead of `checkout`."""
    root = pathlib.Path(checkout).resolve() / ".claude" / "worktrees"
    return {a["name"]: a.get("agent_status") for a in listed
            if WORKER.fullmatch(a.get("name") or "") and pathlib.Path(a.get("cwd") or "/").resolve().is_relative_to(root)}
