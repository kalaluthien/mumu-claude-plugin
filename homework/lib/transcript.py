"""Read a Claude Code session transcript: its entries, their blocks and times."""
import glob
import json
import os
from datetime import datetime

import claude_config

# one constant, so the hook's sentence and the retro's search for it cannot drift apart
SIGNAL = "Wrap-up signal:"


def entries_of(path):
    """The transcript's entries, None when it cannot be read."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def blocks_of(entry, kind):
    body = (entry.get("message") or {}).get("content")
    return [block for block in body if isinstance(block, dict) and block.get("type") == kind] if isinstance(body, list) else []


def text_of(block):
    body = block.get("content")
    return body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)


def seconds(stamp):
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def is_stop(entry):
    return entry.get("subtype") == "stop_hook_summary"


def asked_at(entry):
    """Whether this stop entry carries the hook's ask."""
    return is_stop(entry) and SIGNAL in " ".join(entry.get("hookErrors") or [])


def find(session):
    """The transcript of a session id, or the path itself when one is given."""
    if os.path.exists(session):
        return session
    found = glob.glob(os.path.join(glob.escape(str(claude_config.folder())), "projects", "*", f"{glob.escape(session)}.jsonl"))
    return found[0] if found else None
