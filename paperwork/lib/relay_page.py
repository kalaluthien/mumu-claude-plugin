"""The relay runtime pasted inline into an HTML page, between its marker comments before `</body>`, with the empty data blocks it reads;
a page that holds the paperwork frame between its markers gets the current frame too."""
import pathlib
import re

from page_parts import FRAME_END, FRAME_START, frame

RUNTIME = pathlib.Path(__file__).resolve().parent / "relay-runtime.js"
START, END = "<!-- relay runtime -->", "<!-- /relay runtime -->"
BLOCKS = {"page-data": "{}", "page-threads": '{"threads": {}}'}


def connect(page):
    """Write the current runtime, and the current frame where PAGE holds one, into PAGE, adding the data blocks it lacks, and say
    `connected` when it held no runtime before, else `updated`;
    a page already current is left unwritten, so an open page does not reload for nothing."""
    html = page.read_text()
    copy = f"{START}\n<script>\n{RUNTIME.read_text().strip()}\n</script>\n{END}"
    found = re.search(re.escape(START) + ".*?" + re.escape(END), html, re.S)
    if found:
        updated = html[:found.start()] + copy + html[found.end():]
    else:
        at = html.lower().rfind("</body>")  # the last one, since an earlier one can sit inside a script's string
        updated = html[:at] + copy + "\n" + html[at:] if at >= 0 else html + copy + "\n"
    held = re.search(re.escape(FRAME_START) + ".*?" + re.escape(FRAME_END), updated, re.S)
    if held:
        updated = updated[:held.start()] + frame() + updated[held.end():]
    for name, empty in BLOCKS.items():
        if not re.search(rf"<script\b[^>]*\bid=[\"']{name}[\"']", updated, re.I):
            at = updated.find(START)
            updated = updated[:at] + f'<script type="application/json" id="{name}">\n{empty}\n</script>\n' + updated[at:]
    if updated != html:
        page.write_text(updated)
    return "updated" if found else "connected"


def refuse(word):
    """Refuse NaN and Infinity, which Python reads and a browser's JSON.parse does not."""
    raise ValueError(f"{word} is not JSON")
