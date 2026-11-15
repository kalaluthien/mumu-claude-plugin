#!/usr/bin/env python3
"""Check an HTML page file against the page-changes interface, printing `follows`, or one `break <rule>: <detail>` line per break.

usage: check-page.py <page.html>

Rules: `data-block` (exactly one page-data block, JSON), `threads-block` (at most one page-threads block,
`{"threads": {...}}`), `escape` (no raw `<` inside either block), `anchors` (each `data-id` 1 to 80 letters, digits or
`_.:-`, used once), `thread-keys` (each thread names a `data-id` of the page or an `id` value inside page-data),
`entries` (each entry has `id`, `by` and `text`, each id used once) and `replies` (a `by: "session"` entry's `replies_to`
names an entry of its own thread). Exit 0 when it follows, 1 when it breaks."""
import html.parser
import json
import pathlib
import re
import sys

ANCHOR = re.compile(r"[\w.:-]{1,80}")
BLOCKS = ("page-data", "page-threads")
PARSED = ("handle_starttag", "handle_endtag", "handle_data")  # html.parser calls these by name


class Page(html.parser.HTMLParser):
    """Each `data-id` value as written, and the raw text of each page-data and page-threads script."""

    def __init__(self):
        super().__init__()
        self.anchors, self.blocks, self.inside = [], {name: [] for name in BLOCKS}, None

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if "data-id" in fields:
            self.anchors.append(fields["data-id"] or "")
        if tag == "script" and fields.get("id") in BLOCKS:
            self.inside = {"type": (fields.get("type") or "").lower(), "text": ""}
            self.blocks[fields["id"]].append(self.inside)

    def handle_endtag(self, tag):
        if tag == "script":
            self.inside = None

    def handle_data(self, data):
        if self.inside is not None:
            self.inside["text"] += data


def refuse(word):
    """Refuse NaN and Infinity, which Python reads and a browser's JSON.parse does not."""
    raise ValueError(f"{word} is not JSON")


def parse(name, block, found):
    """The block's JSON, or None after noting why it cannot be read."""
    if block["type"] != "application/json":
        found.append((name, f'#{name} is not type="application/json", so the browser runs it as a script'))
        return None
    if "<" in block["text"]:
        found.append(("escape", f"a raw < in #{name}, where a </script> would end the block; write \\u003c"))
    try:
        return json.loads(block["text"], parse_constant=refuse)
    except ValueError as error:
        found.append((name, f"#{name} does not parse: {error}"))
        return None


def ids_in(value):
    """Every `id` value anywhere inside page-data, as text."""
    if isinstance(value, dict):
        own = {str(value["id"])} if "id" in value else set()
        return own | {each for item in value.values() for each in ids_in(item)}
    if isinstance(value, list):
        return {each for item in value for each in ids_in(item)}
    return set()


def breaks(text):
    """[(rule, detail)] for each way the page breaks the interface."""
    found = []
    page = Page()
    page.feed(text)
    page.close()
    for mark in sorted(set(page.anchors)):
        if not ANCHOR.fullmatch(mark):
            found.append(("anchors", f'data-id "{mark}" is not 1 to 80 letters, digits or _.:-'))
        elif page.anchors.count(mark) > 1:
            found.append(("anchors", f'data-id "{mark}" marks {page.anchors.count(mark)} elements'))
    data_blocks, thread_blocks = page.blocks["page-data"], page.blocks["page-threads"]
    if len(data_blocks) != 1:
        found.append(("data-block", f"{len(data_blocks)} page-data blocks; a page holds exactly one"))
    if len(thread_blocks) > 1:
        found.append(("threads-block", f"{len(thread_blocks)} page-threads blocks; a page holds at most one"))
    data = parse("page-data", data_blocks[0], found) if data_blocks else None
    state = parse("page-threads", thread_blocks[0], found) if thread_blocks else {"threads": {}}
    if state is None:
        return found
    if not isinstance(state, dict) or not isinstance(state.get("threads"), dict):
        return found + [("threads-block", '#page-threads is not {"threads": {...}}')]
    known = set(page.anchors) | ids_in(data)
    seen = {}
    for anchor, thread in state["threads"].items():
        if anchor not in known:
            found.append(("thread-keys", f'thread "{anchor}" names no data-id of the page and no id inside page-data'))
        if not isinstance(thread, list):
            found.append(("entries", f'thread "{anchor}" is not a list'))
            continue
        for entry in thread:
            if not isinstance(entry, dict) or not {"id", "by", "text"} <= set(entry):
                found.append(("entries", f'an entry in thread "{anchor}" lacks id, by or text'))
            elif str(entry["id"]) in seen:
                found.append(("entries", f'entry id {entry["id"]} is used twice'))
            else:
                seen[str(entry["id"])] = anchor
    for anchor, thread in state["threads"].items():
        for entry in thread if isinstance(thread, list) else []:
            if isinstance(entry, dict) and entry.get("by") == "session" and seen.get(str(entry.get("replies_to"))) != anchor:
                found.append(("replies", f'session entry {entry.get("id")} replies to {entry.get("replies_to")}, no entry of thread "{anchor}"'))
    return found


def main(args):
    if len(args) != 1 or args[0].startswith("-") or not pathlib.Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    found = breaks(pathlib.Path(args[0]).read_text())
    for rule, detail in found:
        print(f"break {rule}: {detail}")
    if not found:
        print("follows")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
