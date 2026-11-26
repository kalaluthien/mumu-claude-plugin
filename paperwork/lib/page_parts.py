"""The record card, with its badges, and the search palette a paperwork page draws: the markup, style and code a page script pastes into
its page: the style of `record-card.css` and `record-search.css` before the page's own, and the code of `record-card.js` and
`record-search.js` before the page's, which calls `paperworkCard` and `paperworkSearch`; and the whole page round a skill's own markup and
data blocks."""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
BLOCK = re.compile(r'<script type="application/json" id="page-([\w-]+)">(.*?)</script>', re.DOTALL)
PARTS = ("record-card", "record-search")
CARD = '<aside id="card" role="tooltip"></aside>\n<div id="gloss" role="tooltip"></div>'
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{parts_style}
{style}
</style>
</head>
<body>
{markup}
{palette}
{blocks}
<script>
{parts}
{code}
</script>
</body>
</html>
"""
PALETTE = """<div id="veil"></div>
<div id="palette" role="dialog" aria-label="Search">
<div id="field"><input id="query" type="text" placeholder="{placeholder}" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="hits" aria-autocomplete="list" aria-label="Search">
<button id="regex" class="tool icon quiet" type="button" aria-pressed="false" aria-label="Regular expression" title="Regular expression (Alt+R)">.*</button></div>
<div id="hits" role="listbox"></div>
<footer id="keys"><span><kbd>&uarr;</kbd><kbd>&darr;</kbd> move</span><span><kbd>&crarr;</kbd> open</span><span><kbd>esc</kbd> close</span><span><kbd>alt</kbd><kbd>R</kbd> regex</span></footer>
</div>"""


def palette(placeholder):
    """The search palette's markup, its box saying PLACEHOLDER while empty."""
    return PALETTE.format(placeholder=placeholder.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;"))


def style():
    """The parts' style, to stand before the page's own."""
    return "\n".join((HERE / f"{part}.css").read_text().strip() for part in PARTS)


def code():
    """The parts' code, to run before the page's own."""
    return "\n".join((HERE / f"{part}.js").read_text().strip() for part in PARTS)


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def spread(value):
    """VALUE, an object, as JSON with each field on its own line, and inside it each record of a list on its own, a record that holds
    records spread the same way, so an edit to one record changes only its own line of the page."""
    return "{\n" + ",\n".join(f"{dumps(name)}: {rows(entry)}" for name, entry in value.items()) + "\n}"


def records(value):
    return isinstance(value, list) and bool(value) and all(isinstance(entry, dict) and "id" in entry for entry in value)


def holds(value):
    """Whether VALUE is an object with a list of records somewhere among its fields."""
    return isinstance(value, dict) and any(records(entry) or holds(entry) for entry in value.values())


def rows(value):
    if records(value):
        return "[\n" + ",\n".join(spread(entry) if holds(entry) else dumps(entry) for entry in value) + "\n]"
    return spread(value) if holds(value) else dumps(value)


def block(value, lines=False):
    """JSON that is safe inside a script element, one record per line when LINES."""
    return (spread(value) if lines else dumps(value)).replace("<", "\\u003c")


def earlier(target):
    """The data blocks of the page at TARGET by name, read as JSON: none when no page is there or it keeps no part keys."""
    try:
        found = {name: json.loads(text) for name, text in BLOCK.findall(pathlib.Path(target).read_text())}
    except (OSError, ValueError):
        return {}
    return found if isinstance(found.get("parts"), dict) else {}


def assembled(keyed, before, make, keep):
    """Each part's pieces by name, and the parts made again: a part whose key in KEYED the BEFORE page holds keeps its pieces from it by
    KEEP(name), any other is made by MAKE(name)."""
    pieces, made = {}, []
    for name, key in keyed.items():
        if before.get("parts", {}).get(name) == key:
            pieces[name] = keep(name)
        else:
            pieces[name] = make(name)
            made.append(name)
    return pieces, made


def report(keyed, made):
    """What a build did by part, in prose."""
    kept = [name for name in keyed if name not in made]
    return f"checked and built: {', '.join(made) or 'none'}\nkept from the earlier page: {', '.join(kept) or 'none'}"


def page(assets, title, markup, placeholder, blocks):
    """The standalone page of a skill whose style, code and tag catalogue sit in ASSETS: MARKUP before the search palette, which says
    PLACEHOLDER while empty, then a `page-<name>` data block per entry of BLOCKS, the threads block after the first."""
    named = list(blocks.items())
    named[1:1] = [("threads", {"threads": {}})]
    return PAGE.format(title=title.replace("&", "&amp;").replace("<", "&lt;"), parts_style=style(), style=(assets / "page.css").read_text().strip(),
                       markup=markup, palette=palette(placeholder), parts=code(), code=(assets / "page.js").read_text().strip(),
                       blocks="\n".join(f'<script type="application/json" id="page-{name}">{block(value, name in ("data", "parts"))}</script>' for name, value in named))
