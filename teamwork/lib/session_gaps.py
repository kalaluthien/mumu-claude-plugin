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


def parse_time(text):
    """A GitHub or transcript time; Python before 3.11 cannot read its `Z`."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _scan(root):
    """(project folder, NAME) -> [(first, last, idle gap count)] of its transcripts, oldest first, one pass over the folder."""
    found = collections.defaultdict(list)
    for path in pathlib.Path(root).glob("*/*.jsonl"):
        names, stamps = set(), []
        for line in path.read_text(errors="replace").splitlines():
            if '"agent-name"' not in line and '"timestamp"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("type") == "agent-name":
                names.add(record.get("agentName"))
            elif record.get("type") in ("user", "assistant") and record.get("timestamp"):
                stamps.append(parse_time(record["timestamp"]))
        if stamps:
            stamps.sort()
            idle = sum((later - earlier).total_seconds() / 3600 > IDLE_HOURS for earlier, later in zip(stamps, stamps[1:]))
            for name in names:
                found[(path.parent.name, name)].append((stamps[0], stamps[-1], idle))
    return {key: sorted(sessions) for key, sessions in found.items()}


def _summary(project, name, sessions):
    restart_hours = [max(0.0, (later[0] - earlier[1]).total_seconds() / 3600) for earlier, later in zip(sessions, sessions[1:])]
    return {"worker": name, "project": project, "sessions": len(sessions), "restarts": len(restart_hours),
            "restart_hours": restart_hours, "idle_gaps": sum(session[2] for session in sessions)}


def summaries(root, names=None):
    """Summaries, one per project folder and name, of the names in NAMES or of every named session."""
    return [_summary(project, name, sessions) for (project, name), sessions in sorted(_scan(root).items()) if names is None or name in names]
