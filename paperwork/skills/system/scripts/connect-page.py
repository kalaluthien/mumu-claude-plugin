#!/usr/bin/env python3
"""Paste the relay runtime inline into an HTML page, between its marker comments before `</body>`, and add empty page-data and page-threads blocks when the page lacks them.

usage: connect-page.py <page.html>

It prints `connected <page>` when the page had no runtime and `updated <page>` when an older copy between the markers
was replaced; a page already current is left unwritten, so an open page does not reload for nothing."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from relay_page import connect  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if len(args) != 1 or args[0].startswith("-") or not pathlib.Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    page = pathlib.Path(args[0])
    print(f"{connect(page)} {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
