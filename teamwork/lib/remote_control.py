"""Whether a Claude Code session has Remote Control, which is what lets the owner away from the machine receive a push."""
import json

import claude_config


def active(session_id):
    """True when the live session record of SESSION_ID names a bridge session, which Claude Code writes while the session is connected to Remote Control."""
    if not session_id:
        return False
    for path in (claude_config.folder() / "sessions").glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if record.get("sessionId") == session_id:
            return bool(record.get("bridgeSessionId"))
    return False
