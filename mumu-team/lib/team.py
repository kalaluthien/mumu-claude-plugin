"""What the `worker-watch` and `lead-heartbeat` monitors share: the lead's mission, each worker's word, and the poll loop.

The mission is `<plugin data dir>/mission/$CLAUDE_CODE_SESSION_ID.md`. A
leader's reads one `Mission: leader of <parent-url>` line per parent it holds, and one
`Worker: <name> <issue-url>` line per worker; a worker's reads
`Mission: worker ...`, and a monitor in its session exits at once.
`MONITOR_POLL` sets the poll interval in seconds (10), `MONITOR_WAIT` how long
a monitor waits for a mission file before it exits (600), and `MONITOR_TICKS`
stops the loop after that many polls, for a test (unset: never).
"""
import json
import os
import pathlib
import subprocess
import time

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}


def read_mission(text):
    """`([parent-url, ...], {name: issue-url})` of a leader's mission, or None for a worker's."""
    parents, workers = [], {}
    for line in text.splitlines():
        if line.startswith("Mission: worker"):
            return None
        if line.startswith("Mission: leader"):
            parents.append(line.split()[-1])
        fields = line.split()
        if fields[:1] == ["Worker:"] and len(fields) >= 3:
            workers[fields[1]] = fields[2]
    return parents, workers


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
    """Call `tick(parents, workers, words, now)` every poll while a leader's mission exists, and print the lines it returns.

    Returns when the mission is a worker's, when a mission file once seen is
    gone (Lead 5 deletes it, so `/exit` meets no running monitor), when no
    mission file appears within `MONITOR_WAIT` seconds (a worker that never
    wrote one), or after `MONITOR_TICKS` polls. A poll with no parent yet (Lead
    1's `Goal:` stub), or whose `herdr agent list` fails, is skipped.
    """
    mission = pathlib.Path(data_dir, "mission", os.environ["CLAUDE_CODE_SESSION_ID"] + ".md")
    interval = float(os.environ.get("MONITOR_POLL", 10))
    ticks = int(os.environ.get("MONITOR_TICKS", 0))
    wait = float(os.environ.get("MONITOR_WAIT", 600))
    last, n, seen, start = {}, 0, False, time.time()
    while not ticks or n < ticks:
        n += 1
        exists = mission.exists()
        read = read_mission(mission.read_text()) if exists else ([], {})
        if read is None or seen and not exists or not seen and time.time() - start >= wait:
            return
        seen = seen or exists
        listed = agents() if read[0] else None
        if listed is not None:
            last = words(last, read[1], listed)
            for line in tick(*read, last, time.time()):
                print(line, flush=True)
        time.sleep(interval)
