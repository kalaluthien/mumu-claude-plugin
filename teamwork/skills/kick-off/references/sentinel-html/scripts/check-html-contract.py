#!/usr/bin/env python3
"""Check an HTML page file against interactive-html-contract.md, printing one `break <rule>: <detail>` line per break, then `follows` or `breaks <n>`.

usage: check-html-contract.py <page.html>
usage: check-html-contract.py fixtures

`fixtures` checks each page in the `fixtures/` folder beside this script's folder: a `follows-*.html` page must show no break, and
a `break-<rule>[-<case>].html` page exactly one break, of its rule; it prints PASS when every page does, else FAIL naming each."""
import html.parser
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
BLOCK = re.compile(r'(<script\b(?=[^>]*\bid=["\']page-threads["\'])[^>]*>)(.*?)</script>', re.S | re.I)
RUNS = ("text/javascript", "application/javascript", "module")
ANCHOR = re.compile(r"[\w.:-]{1,80}")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HEADINGS = {"h1", "h2", "h3"}
PARTS = {"section", "article", "figure", "table"}
PARSED = ("handle_starttag", "handle_endtag", "handle_startendtag", "handle_data")  # html.parser calls these by name
RULES = ("one-block", "block", "conversation-only", "escape", "entries", "replies", "anchors")


class Elements(html.parser.HTMLParser):
    """The page's elements that can take an anchor, in document order, each with its parent, its text and its first heading."""

    def __init__(self):
        super().__init__()
        self.open, self.found, self.marks, self.gone, self.blocks, self.scripts = [], [], [], [], [], []

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        mark = fields["data-thread-anchor"] or "" if "data-thread-anchor" in fields else None  # a mark with no value reads as "" in the browser
        if mark is not None:
            self.marks.append(mark)
            if "data-thread-gone" in fields:
                self.gone.append(mark)
        if tag in VOID:
            if mark is not None:
                self.found.append({"tag": tag, "id": fields.get("id") or "", "mark": mark, "text": [], "heading": None, "parent": self.open[-1] if self.open else None})
            return
        if tag == "script":
            self.scripts.append(fields)
            if fields.get("id") == "page-threads":
                self.blocks.append({"type": fields.get("type") or "", "text": []})
        node = {"tag": tag, "id": fields.get("id") or "", "mark": mark, "text": [], "heading": None,
                "parent": self.open[-1] if self.open else None}
        if tag in HEADINGS:
            for each in self.open:
                each["heading"] = each["heading"] or node
        if tag in HEADINGS or node["mark"] is not None or (tag in PARTS and node["id"]):
            self.found.append(node)
        self.open.append(node)

    def handle_endtag(self, tag):
        if any(each["tag"] == tag for each in self.open):
            while self.open.pop()["tag"] != tag:
                pass

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.blocks and self.open and self.open[-1]["tag"] == "script" and self.open[-1]["id"] == "page-threads":
            self.blocks[-1]["text"].append(data)
        for each in self.open:
            each["text"].append(data)


def anchors(parser):
    """The anchor ids the page has as written: each mark, and a derived id for each unmarked part or heading."""
    taken = {node["mark"] for node in parser.found if node["mark"] is not None}
    for node in parser.found:
        near = node
        while near and near.get("anchor", near["mark"]) is None:
            near = near["parent"]
        if node["mark"] is not None or (near and near["tag"] in ("section", "article")):
            continue
        title = unicodedata.normalize("NFC", "".join((node["heading"] or node)["text"])).strip()
        words = re.sub(r"^-|-$", "", re.sub(r"[\W_]+", "-", title.lower()))[:60]
        first = node["id"] if ANCHOR.fullmatch(node["id"]) else f"h-{words}" if words else "h"
        slug, n = first, 2
        while slug in taken:
            slug, n = f"{first}-{n}", n + 1
        taken.add(slug)
        node["anchor"] = slug
    return taken


def unknown(word):
    """Refuse NaN and Infinity, which Python reads and a browser's JSON.parse does not."""
    raise ValueError(f"{word} is not JSON")


def breaks(html):
    """[(rule, detail)] for each way the page breaks the contract."""
    found = []
    parser = Elements()
    parser.feed(html)
    parser.close()
    blocks = ["".join(block["text"]) for block in parser.blocks]
    if len(blocks) > 1:
        found.append(("one-block", f"{len(blocks)} thread blocks; the server and the sentinel edit only the first"))
    first = BLOCK.search(html)
    if blocks and first and first.group(2) != blocks[0]:
        found.append(("one-block", "text that reads as a thread block, in a comment or a string, sits before the real one; the server edits the first it reads"))
    marks = parser.marks
    for mark in sorted(set(marks)):
        if not ANCHOR.fullmatch(mark):
            found.append(("anchors", f'"{mark}" is not 1 to 80 letters, digits or _.:-'))
        elif marks.count(mark) > 1:
            found.append(("anchors", f'"{mark}" marks {marks.count(mark)} elements'))
    if not blocks:
        return found
    if parser.blocks[0]["type"].lower() != "application/json":
        found.append(("block", 'the thread block is not type="application/json", so the browser runs it as a script'))
    body = blocks[0]
    if "<" in body:
        found.append(("escape", "a raw < in the thread block, where a </script> in a comment would end it; write \\u003c"))
    try:
        state = json.loads(body, parse_constant=unknown)
    except ValueError as error:
        return found + [("block", f"the thread block does not parse: {error}")]
    if not isinstance(state, dict) or not isinstance(state.get("threads"), dict):
        return found + [("block", 'the thread block is not {"threads": {...}}')]
    extra = sorted(set(state) - {"threads"})
    if extra:
        found.append(("conversation-only", f"the thread block holds {', '.join(extra)}; keep the page's content in its own HTML or data block"))
    ids = {}
    written = anchors(parser)
    # a page with no mark on a part it holds, whose own script runs, may make its anchors in the browser, which a file cannot show
    made = len(marks) == len(parser.gone) and any((fields.get("type") or "text/javascript").lower() in RUNS for fields in parser.scripts)
    for anchor, thread in state["threads"].items():
        if anchor not in written and not made:
            found.append(("anchors", f'thread "{anchor}" names no anchor of the page; if its part was removed, leave <span hidden data-thread-gone data-thread-anchor="{anchor}"></span> where it was'))
        if not isinstance(thread, list):
            found.append(("entries", f'thread "{anchor}" is not a list'))
            continue
        for entry in thread:
            if not isinstance(entry, dict) or not {"id", "by", "text"} <= set(entry):
                found.append(("entries", f'an entry in "{anchor}" lacks id, by or text'))
                continue
            if str(entry["id"]) in ids:
                found.append(("entries", f'id {entry["id"]} is used twice'))
            ids[str(entry["id"])] = anchor
    for anchor, thread in state["threads"].items():
        for entry in thread if isinstance(thread, list) else []:
            if isinstance(entry, dict) and entry.get("by") == "sentinel" and ids.get(str(entry.get("replies_to"))) != anchor:
                found.append(("replies", f'sentinel entry {entry.get("id")} answers {entry.get("replies_to")}, no entry of thread "{anchor}"'))
    return found


def replay():
    folder = HERE.parent / "fixtures"
    pages = sorted(folder.glob("*.html"))
    wrong = []
    for page in pages:
        rules = sorted(rule for rule, _ in breaks(page.read_text()))
        name = page.stem.removeprefix("break-")
        expected = [] if page.name.startswith("follows-") else [max((rule for rule in RULES if name == rule or name.startswith(rule + "-")), key=len, default=name)]
        print(f"{page.name}: {', '.join(rules) or 'follows'}")
        if rules != expected:
            wrong.append(f"{page.name} shows {rules or 'no break'}, expected {expected or 'no break'}")
    missing = [rule for rule in RULES if not list(folder.glob(f"break-{rule}.html")) + list(folder.glob(f"break-{rule}-*.html"))]
    if missing:
        wrong.append(f"no fixture breaks {', '.join(missing)}")
    if not any(page.name.startswith("follows-") for page in pages):
        wrong.append("no fixture follows the contract")
    print(f"FAIL: {'; '.join(wrong)}" if wrong else "PASS")
    return 1 if wrong else 0


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    if args[0] == "fixtures":
        return replay()
    page = pathlib.Path(args[0])
    if not page.is_file():
        print(__doc__, file=sys.stderr)
        return 2
    found = breaks(page.read_text())
    for rule, detail in found:
        print(f"break {rule}: {detail}")
    print(f"breaks {len(found)}" if found else "follows")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
