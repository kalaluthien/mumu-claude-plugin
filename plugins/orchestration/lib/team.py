"""What the `worker-watch` and `lead-heartbeat` monitors share: the lead's mission, each worker's word, and the poll loop.

The mission is `<plugin data dir>/mission/$CLAUDE_CODE_SESSION_ID.md`. A
leader's reads `Mission: leader of <parent-url>` and holds one
`Worker: <name> <issue-url>` line per worker; a worker's reads
`Mission: worker ...`, and a monitor in its session exits at once.
`MONITOR_POLL` sets the poll interval in seconds (10).
"""
import json
import os
import pathlib
import subprocess
import time

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}


def read_mission(text):
    """`(parent-url, {name: issue-url})` of a leader's mission, or None for a worker's."""
    parent, workers = None, {}
    for line in text.splitlines():
        if line.startswith("Mission: worker"):
            return None
        if line.startswith("Mission: leader"):
            parent = line.split()[-1]
        fields = line.split()
        if fields[:1] == ["Worker:"] and len(fields) >= 3:
            workers[fields[1]] = fields[2]
    return parent, workers


def words(last, workers, agents):
    """Each worker's word from herdr's `{name: agent_status}`: `blocked`, `idle`, `working`, or `gone` when not listed.

    `unknown` keeps the `last` word, and a worker not yet seen is `working`.
    """
    return {name: WORD.get(agents[name], last.get(name, "working")) if name in agents else "gone" for name in workers}


def agents():
    """herdr's `{name: agent_status}`, or None when `herdr agent list` cannot be run or read."""
    try:
        listed = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True)
        return {a.get("name"): a["agent_status"] for a in json.loads(listed.stdout)["result"]["agents"]}
    except (OSError, ValueError, KeyError):
        return None


def poll(data_dir, tick):
    """Call `tick(parent, workers, words, now)` every poll while a leader's mission exists, and print the lines it returns.

    Returns when the mission is a worker's. A poll with no mission, or whose
    `herdr agent list` fails, is skipped.
    """
    mission = pathlib.Path(data_dir, "mission", os.environ["CLAUDE_CODE_SESSION_ID"] + ".md")
    interval = float(os.environ.get("MONITOR_POLL", 10))
    last = {}
    while True:
        read = read_mission(mission.read_text()) if mission.exists() else ()
        if read is None:
            return
        listed = agents() if read else None
        if listed is not None:
            last = words(last, read[1], listed)
            for line in tick(*read, last, time.time()):
                print(line, flush=True)
        time.sleep(interval)
