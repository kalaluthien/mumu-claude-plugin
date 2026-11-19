"""Read a Claude Code session transcript: its entries, their blocks and times."""
import glob
import json
import os
import re
from datetime import datetime

import claude_config

# one constant, so the hook's sentence and the retro's search for it cannot drift apart
SIGNAL = "Wrap-up signal:"
# the words code writes when it refuses a step (a hook, a permission check, the auto mode classifier, a script that
# posts or runs nothing); one constant, so the retro and the dream count the same refusals as handled
REFUSED_BY_CODE = re.compile(r"hook error|<tool_use_error>Blocked|denied by (?:the )?(?:Claude Code )?auto mode|denied by a built-in"
                             r"|Blocked by classifier|classifier denied|Permission (?:to use \w+|for this \w+)\b.{0,300}? has been denied"
                             r"|requested permissions|contains multiple operations|requires approval|nothing in this command ran|nothing posted")


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
