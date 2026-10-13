"""Restarts of a worker, read from the transcripts under a Claude projects folder.

A session is one transcript file named by the worker (its `agent-name` record); a restart is a further session of the
same name, and costs the hours from the last message of one session to the first of the next. A pause inside a session
is an idle gap: the worker waited, nothing restarted."""
import json
import pathlib
from datetime import datetime

IDLE_HOURS = 0.5


def _time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _sessions(root, name):
    """(first, last, idle gap count) of each transcript of NAME, oldest first."""
    found = []
    for path in pathlib.Path(root).glob("*/*.jsonl"):
        text = path.read_text(errors="replace")
        if name not in text:
            continue
        stamps, named = [], False
        for line in text.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            named = named or (rec.get("type") == "agent-name" and rec.get("agentName") == name)
            if rec.get("type") in ("user", "assistant") and rec.get("timestamp"):
                stamps.append(_time(rec["timestamp"]))
        if named and stamps:
            stamps.sort()
            idle = sum((b - a).total_seconds() / 3600 > IDLE_HOURS for a, b in zip(stamps, stamps[1:]))
            found.append((stamps[0], stamps[-1], idle))
    return sorted(found)


def summary(root, name):
    """None when NAME has no transcript, else its sessions, restarts, restart hours and idle gaps."""
    sessions = _sessions(root, name)
    if not sessions:
        return None
    restart_hours = [max(0.0, (b[0] - a[1]).total_seconds() / 3600) for a, b in zip(sessions, sessions[1:])]
    return {"worker": name, "sessions": len(sessions), "restarts": len(restart_hours),
            "restart_hours": restart_hours, "idle_gaps": sum(s[2] for s in sessions)}
