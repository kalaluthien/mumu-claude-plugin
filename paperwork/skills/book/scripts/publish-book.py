#!/usr/bin/env python3
"""Put a reviewed book.html on a host and record what went there.

usage: publish-book.py file DIR --to PATH [--dry-run]                copy book.html to PATH, verify the copy
usage: publish-book.py static DIR --to OUTDIR [--url URL] [--dry-run]  OUTDIR/index.html for any static host; URL is where the host serves it
usage: publish-book.py claude-artifact DIR [--dry-run]               write the page fragment, print the Artifact tool call to make
usage: publish-book.py record TARGET DIR --url URL [--sha SHA]       record a publish a host tool made (default SHA: the current build)
usage: publish-book.py status DIR                                    each record, and whether it matches the current build

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
