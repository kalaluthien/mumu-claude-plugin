"""What the `worker-watch` and `lead-heartbeat` monitors share: the lead's mission, herdr's agents, and the poll loop.

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


def read_mission(text):
    """`(parent-url, {name: issue-url})` of a leader's mission, or None for a worker's."""
    parent, workers = None, {}
    for line in text.splitlines():
        if line.startswith("Mission: worker"):
            return None
        if line.startswith("Mission: leader"):
            parent = line.split()[-1]
        if line.startswith("Worker: "):
            name, url = line.split()[1:3]
            workers[name] = url
    return parent, workers


def poll(data_dir, tick):
    """Call `tick(parent, workers, agents, now)` every poll while a leader's mission exists, and print the lines it returns.

    Returns when the mission is a worker's. A poll with no mission, or whose
    `herdr agent list` fails, is skipped.
    """
    mission = pathlib.Path(data_dir, "mission", os.environ["CLAUDE_CODE_SESSION_ID"] + ".md")
    interval = float(os.environ.get("MONITOR_POLL", 10))
    while True:
        read = read_mission(mission.read_text()) if mission.exists() else ()
        if read is None:
            return
        listed = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True)
        if read and listed.returncode == 0:
            agents = {a.get("name"): a["agent_status"] for a in json.loads(listed.stdout)["result"]["agents"]}
            for line in tick(*read, agents, time.time()):
                print(line, flush=True)
        time.sleep(interval)
