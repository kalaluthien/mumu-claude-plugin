#!/usr/bin/env python3
"""The `watch-team` monitor: tell a manager each change of its workers, the sessions in its workspace.

It prints `<working|idle|blocked> <name>` and `gone <name>` on each change, `team idle <m>m` while no worker works,
and `usage reset <HH:MM>` once a usage limit that stopped the team has passed. It stays silent in a session whose
name does not end in `-manager`, since a worker starts the same skill."""
import datetime
import glob
import json
import os
import pathlib
import subprocess
import time

POLL, IDLE, REPEAT = float(os.environ.get("MONITOR_POLL", 10)), float(os.environ.get("TEAM_WATCH_IDLE", 1200)), 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}
CONFIG = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")


def agents():
    p = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True)
    return json.loads(p.stdout)["result"]["agents"]


def reset_at(session):
    """The reset time of a usage-limit rejection that is the session's last reply, else None."""
    found = glob.glob(str(CONFIG / "projects" / "*" / f"{glob.escape(session)}.jsonl"))
    if not found:
        return None
    with open(found[0], "rb") as f:
        f.seek(max(0, os.path.getsize(found[0]) - 256 * 1024))  # the tail holds the last reply
        lines = f.read().decode("utf-8", "replace").splitlines()
    at = None
    for line in lines:
        if '"assistant"' in line:
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # cut at the tail's start
            quota = entry.get("quotaLimits") if isinstance(entry, dict) and entry.get("type") == "assistant" else None
            at = quota.get("resetsAt") if isinstance(quota, dict) and quota.get("status") == "rejected" else None
    return at if isinstance(at, (int, float)) else None


def main():
    last, quiet_since, told, waiting = {}, None, None, set()
    while True:
        try:
            listed = agents()
        except (OSError, ValueError, KeyError):
            time.sleep(POLL)
            continue
        me = next((a for a in listed if a.get("pane_id") == os.environ.get("HERDR_PANE_ID")), {})
        if not (me.get("name") or "").endswith("-manager"):
            time.sleep(POLL)
            continue
        team = {a["name"]: a for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")}
        words = {n: WORD.get(a.get("agent_status"), last.get(n, "working")) for n, a in team.items()}
        lines = [f"{w} {n}" for n, w in words.items() if w != last.get(n, "working")]
        lines += [f"gone {n}" for n in last if n not in words]
        last, now = words, time.time()
        for a in [me, *team.values()]:
            if (at := reset_at((a.get("agent_session") or {}).get("value") or "")) and at > now:
                waiting.add(at)
        for at in sorted(t for t in waiting if t + 60 <= now):  # a minute's margin for the limit to lift
            waiting.discard(at)
            lines.append(f"usage reset {datetime.datetime.fromtimestamp(at).strftime('%H:%M')}")
        if "working" in words.values():
            quiet_since = told = None
        else:
            quiet_since = quiet_since or now
            if now - quiet_since >= IDLE and (told is None or now - told >= REPEAT):
                told = now
                lines.append(f"team idle {int((now - quiet_since) // 60)}m")
        for line in lines:
            print(line, flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
