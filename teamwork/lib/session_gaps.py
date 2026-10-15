"""Restarts of a named session, read from the transcripts under a Claude projects folder.

A session is one transcript file named by its `agent-name` record; a restart is a further session of the same name in the
same project folder, since one name may serve two repositories, and
costs the hours from the last message of one session to the first of the next. A pause inside a session is an idle gap:
the session waited, nothing restarted."""
import collections
import json
import pathlib
from datetime import datetime

IDLE_HOURS = 0.5


def _scan(root):
    """(project folder, NAME) -> [(first, last, idle gap count)] of its transcripts, oldest first, one pass over the folder."""
    found = collections.defaultdict(list)
    for path in pathlib.Path(root).glob("*/*.jsonl"):
        names, stamps = set(), []
        for line in path.read_text(errors="replace").splitlines():
            if '"agent-name"' not in line and '"timestamp"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") == "agent-name":
                names.add(rec.get("agentName"))
            elif rec.get("type") in ("user", "assistant") and rec.get("timestamp"):
                stamps.append(datetime.fromisoformat(rec["timestamp"]))
        if stamps:
            stamps.sort()
            idle = sum((b - a).total_seconds() / 3600 > IDLE_HOURS for a, b in zip(stamps, stamps[1:]))
            for name in names:
                found[(path.parent.name, name)].append((stamps[0], stamps[-1], idle))
    return {key: sorted(s) for key, s in found.items()}


def _summary(project, name, sessions):
    restart_hours = [max(0.0, (b[0] - a[1]).total_seconds() / 3600) for a, b in zip(sessions, sessions[1:])]
    return {"worker": name, "project": project, "sessions": len(sessions), "restarts": len(restart_hours),
            "restart_hours": restart_hours, "idle_gaps": sum(s[2] for s in sessions)}


def summaries(root, names=None):
    """Summaries, one per project folder and name, of the names in NAMES or of every named session."""
    return [_summary(p, n, s) for (p, n), s in sorted(_scan(root).items()) if names is None or n in names]
