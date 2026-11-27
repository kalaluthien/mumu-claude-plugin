"""The frame every paperwork page shares and the whole page a skill builds round it. The frame is one block of the page's head, between
FRAME_START and FRAME_END: the style of the tokens, the frame, the record card and the search, then their code, which a page's own script
calls as `paperworkFrame(options)`; `frame()` writes it, `relay_page.connect` refreshes it in a page that holds it, and `page()` builds a
skill's page with it."""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
BLOCK = re.compile(r'<script type="application/json" id="page-([\w-]+)">(.*?)</script>', re.DOTALL)
STYLES = ("page-tokens", "page-frame", "record-card", "record-search")
SCRIPTS = ("record-card", "record-search", "page-frame")
FRAME_START, FRAME_END = "<!-- page frame -->", "<!-- /page frame -->"
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{frame}
<style>
{style}
</style>
</head>
<body>
{markup}
{blocks}
<script>
{code}
</script>
</body>
</html>
"""


def frame():
    """The frame block, markers included."""
    style = "\n".join((HERE / f"{name}.css").read_text().strip() for name in STYLES)
    code = "\n".join((HERE / f"{name}.js").read_text().strip() for name in SCRIPTS)
    return f"{FRAME_START}\n<style>\n{style}\n</style>\n<script>\n{code}\n</script>\n{FRAME_END}"


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


def page(assets, title, markup, blocks):
    """The standalone page of a skill whose style, code and tag catalogue sit in ASSETS: the frame, then MARKUP, then a `page-<name>`
    data block per entry of BLOCKS, the threads block after the first."""
    named = list(blocks.items())
    named[1:1] = [("threads", {"threads": {}})]
    return PAGE.format(title=title.replace("&", "&amp;").replace("<", "&lt;"), frame=frame(), style=(assets / "page.css").read_text().strip(),
                       markup=markup, code=(assets / "page.js").read_text().strip(),
                       blocks="\n".join(f'<script type="application/json" id="page-{name}">{block(value, name in ("data", "parts"))}</script>' for name, value in named))
