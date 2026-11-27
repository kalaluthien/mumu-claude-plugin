#!/usr/bin/env python3
"""Queue the change events an open HTML page sends for a Claude Code session to apply, and tell the page to reload when its file changes.

usage: serve-relay.py <page.html> [--port <n>] [--quiet <seconds>]

It binds 127.0.0.1 behind a random token, `http://127.0.0.1:<port>/<token>/`, written to `url.txt` beside the page and
reused on a restart. Its first stdout line is `relay url: <url>`, its second `relay page: <file url>`, the page's
`file://` url that opens it standalone; once a change is queued and `--quiet` seconds
(default 3) pass with no newer one, it prints one `relay pending ...` line carrying the commands that pull and
ack the queue. It never writes the page: each version of it is copied, read only, into `history/`; events wait in
`changes/pending.jsonl` and acked ones move to `changes/applied.jsonl`."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from relay_server import serve  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if not args or args[0].startswith("-"):
        return usage()
    page = pathlib.Path(args[0]).resolve()
    port, quiet, rest = 0, 3.0, args[1:]
    while rest:
        flag, value = rest.pop(0), rest.pop(0) if rest else ""
        if flag == "--port" and value.isdigit():
            port = int(value)
        elif flag == "--quiet" and re.fullmatch(r"\d+(\.\d+)?", value):
            quiet = float(value)
        else:
            return usage()
    if not page.is_file():
        return usage()
    return serve(page, port, quiet)


def usage():
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
