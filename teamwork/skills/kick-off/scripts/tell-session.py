#!/usr/bin/env python3
"""Tell a session herdr lists the text in the file, once it is idle or done, and print `delivered to <name>`, with how, or
`not delivered to <name>: <reason>` and exit 1, at once for a session of the kind the team runs, which its own message adapter tells. TELL_SESSION_TIMEOUT (default 600) bounds the wait in seconds.

usage: tell-session.py <name> <text-file>"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import message_herdr  # noqa: E402


def main(args):
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    name, text = args[0], pathlib.Path(args[1]).read_text().strip()
    delivered, how = message_herdr.tell(name, text, float(os.environ.get("TELL_SESSION_TIMEOUT", 600)))
    if not delivered:
        sys.exit(f"not delivered to {name}: {how}")
    print(" ".join(filter(None, ["delivered to", name, how])))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
