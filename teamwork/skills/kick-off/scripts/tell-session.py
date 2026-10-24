#!/usr/bin/env python3
"""usage: tell-session.py <name> <text-file>

Tell a session herdr lists the text in the file, once it is idle or done, and print `delivered to <name>`, with how, or
`not delivered to <name>: <reason>` and exit 1. TELL_SESSION_TIMEOUT (default 600) bounds the wait in seconds."""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import message_herdr  # noqa: E402

if len(sys.argv) != 3:
    sys.exit(__doc__.splitlines()[0])
name, text = sys.argv[1], pathlib.Path(sys.argv[2]).read_text().strip()
delivered, how = message_herdr.tell(name, text, float(os.environ.get("TELL_SESSION_TIMEOUT", 600)))
if not delivered:
    sys.exit(f"not delivered to {name}: {how}")
print(" ".join(filter(None, ["delivered to", name, how])))
