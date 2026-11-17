#!/usr/bin/env python3
"""Paste the relay runtime inline into an HTML page, between its marker comments before `</body>`, and add empty page-data and page-threads blocks when the page lacks them.

usage: connect-page.py <page.html>

It prints `connected <page>` when the page had no runtime and `updated <page>` when an older copy between the markers
was replaced; a page already current is left unwritten, so an open page does not reload for nothing."""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
START, END = "<!-- relay runtime -->", "<!-- /relay runtime -->"
BLOCKS = {"page-data": "{}", "page-threads": '{"threads": {}}'}


def main(args):
    if len(args) != 1 or args[0].startswith("-") or not pathlib.Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    page = pathlib.Path(args[0])
    html = page.read_text()
    runtime = (HERE.parent / "assets" / "page-runtime.js").read_text().strip()
    copy = f"{START}\n<script>\n{runtime}\n</script>\n{END}"
    found = re.search(re.escape(START) + ".*?" + re.escape(END), html, re.S)
    if found:
        updated = html[:found.start()] + copy + html[found.end():]
    else:
        at = html.lower().rfind("</body>")  # the last one, since an earlier one can sit inside a script's string
        updated = html[:at] + copy + "\n" + html[at:] if at >= 0 else html + copy + "\n"
    for name, empty in BLOCKS.items():
        if not re.search(rf"<script\b[^>]*\bid=[\"']{name}[\"']", updated, re.I):
            at = updated.find(START)
            updated = updated[:at] + f'<script type="application/json" id="{name}">\n{empty}\n</script>\n' + updated[at:]
    if updated != html:
        page.write_text(updated)
    print(f"{'updated' if found else 'connected'} {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
