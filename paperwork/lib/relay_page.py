"""The relay runtime pasted inline into an HTML page, between its marker comments before `</body>`, with the empty data blocks it reads."""
import pathlib
import re

RUNTIME = pathlib.Path(__file__).resolve().parent / "relay-runtime.js"
START, END = "<!-- relay runtime -->", "<!-- /relay runtime -->"
BLOCKS = {"page-data": "{}", "page-threads": '{"threads": {}}'}


def connect(page):
    """Write the current runtime into PAGE, adding the data blocks it lacks, and say `connected` when it held none before, else `updated`;
    a page already current is left unwritten, so an open page does not reload for nothing."""
    html = page.read_text()
    copy = f"{START}\n<script>\n{RUNTIME.read_text().strip()}\n</script>\n{END}"
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
    return "updated" if found else "connected"
