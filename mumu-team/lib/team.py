"""What the `worker-watch` and `lead-heartbeat` monitors share: the lead's mission, each worker's word, and the poll loop.

The mission is `<plugin data dir>/mission/$CLAUDE_CODE_SESSION_ID.md`. A
leader's reads one `MISSION: leader of <parent-url>` line per parent it holds, and one
`SUBSCRIBE: <name> <issue-url>` line per worker, which `worker-start.py`
writes and `worker-close.py` removes; a worker's reads
`MISSION: worker ...`, and a monitor in its session exits at once, as it does
before any poll when `MUMU_ROLE=worker`, which `worker-start.py` sets on the tab.
`MONITOR_POLL` sets the poll interval in seconds (10), `MONITOR_WAIT` how long
a monitor waits for a mission file before it exits (600), and `MONITOR_TICKS`
stops the loop after that many polls, for a test (unset: never).
Each key is read in any case, so a mission written `Mission:` still counts.
"""
import json
import os
import pathlib
import subprocess
import time

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}


FORMS = ("GOAL: <goal>", "MISSION: leader of <parent-url>", "MISSION: worker on <issue-url>",
         "EXPECT: <expectations>", "SUBSCRIBE: <name> <issue-url>")


def kind(line):
    """What a mission line is: `blank`, `goal`, `leader`, `worker`, `expect`, `subscribe`, or None for a line none of `FORMS` matches."""
    fields = line.split()
    key = fields[0].upper() if fields else ""
    if not fields:
        return "blank"
    if key in ("GOAL:", "EXPECT:"):
        return key[:-1].lower()
    if key == "MISSION:" and len(fields) == 4 and fields[1:3] in (["leader", "of"], ["worker", "on"]):
        return fields[1]
    if key == "SUBSCRIBE:" and len(fields) == 3:
        return "subscribe"
    return None


def unrecognised(text):
    """The lines of a mission that `kind` does not recognise, which `read_mission` skips."""
    return [line for line in text.splitlines() if kind(line) is None]


def read_mission(text):
    """`([parent-url, ...], {name: issue-url})` of a leader's mission, or None for a worker's."""
    parents, workers = [], {}
    for line in text.splitlines():
        k, fields = kind(line), line.split()
        if k == "worker":
            return None
        if k == "leader":
            parents.append(fields[-1])
        if k == "subscribe":
            workers[fields[1]] = fields[2]
    return parents, workers


def mission_file(session=None):
    """The mission of `session` (this one's, `$CLAUDE_CODE_SESSION_ID`, by default), found as `<config dir>/plugins/data/*/mission/<session>.md`, or None.

    A script run from the lead's Bash has no `CLAUDE_PLUGIN_DATA`, and the
    session id is unique, so the glob finds at most one.
    """
    config = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")
    session = session or os.environ["CLAUDE_CODE_SESSION_ID"]
    return next(iter(sorted(config.glob(f"plugins/data/*/mission/{session}.md"))), None)


def subscribed(line, name):
    """Whether `line` is a `SUBSCRIBE: <name> ...` line, in any case."""
    fields = line.split()
    return len(fields) >= 2 and fields[0].upper() == "SUBSCRIBE:" and fields[1] == name


def subscribe(path, name, url):
    """Append `SUBSCRIBE: <name> <url>` to the mission at `path`, unless a line for `name` is there."""
    text = path.read_text()
    if not any(subscribed(line, name) for line in text.splitlines()):
        path.write_text(text + ("\n" if text and not text.endswith("\n") else "") + f"SUBSCRIBE: {name} {url}\n")


def unsubscribe(path, name):
    """Remove every `SUBSCRIBE: <name> ...` line from the mission at `path`."""
    lines = path.read_text().splitlines(keepends=True)
    path.write_text("".join(line for line in lines if not subscribed(line, name)))


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
    1's `GOAL:` stub), or whose `herdr agent list` fails, is skipped.
    """
    if os.environ.get("MUMU_ROLE") == "worker":
        return
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
