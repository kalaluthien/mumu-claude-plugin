#!/usr/bin/env python3
"""Put a reviewed book.html on a host and record what went there.


Every publish writes DIR/publish.json: {TARGET: {target, url, sha, at}}. `make-book.py approve publish` refuses unless a record's sha equals the current build's.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from book import publish  # noqa: E402


def main(args):
    try:
        return publish.main(args)
    except SystemExit as stop:
        if stop.code == 2:
            print(__doc__, file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
