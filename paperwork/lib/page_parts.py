"""The record card, with its badges, and the search palette a paperwork page draws: the markup, style and code a page script pastes into
its page: the style of `record-card.css` and `record-search.css` before the page's own, and the code of `record-card.js` and
`record-search.js` before the page's, which calls `paperworkCard` and `paperworkSearch`; and the whole page round a skill's own markup and
data blocks."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
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


def block(value):
    """JSON that is safe inside a script element."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def page(assets, title, markup, placeholder, blocks):
    """The standalone page of a skill whose style, code and tag catalogue sit in ASSETS: MARKUP before the search palette, which says
    PLACEHOLDER while empty, then a `page-<name>` data block per entry of BLOCKS, the threads block after the first."""
    named = list(blocks.items())
    named[1:1] = [("threads", {"threads": {}})]
    return PAGE.format(title=title.replace("&", "&amp;").replace("<", "&lt;"), parts_style=style(), style=(assets / "page.css").read_text().strip(),
                       markup=markup, palette=palette(placeholder), parts=code(), code=(assets / "page.js").read_text().strip(),
                       blocks="\n".join(f'<script type="application/json" id="page-{name}">{block(value)}</script>' for name, value in named))
