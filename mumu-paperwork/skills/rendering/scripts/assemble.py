#!/usr/bin/env python3
r"""Print one widget's spec, or wrap a page's body in the skin and the code of each widget it uses.

usage: assemble.py --spec <widget> | assemble.py <body.html> <page.html>
The widgets are page (the shell), chart, filter, controls, source and each diagram kind; the body is what goes inside <main>.
A body with TeX, \( … \) or \[ … \], also gets KaTeX: its script from jsdelivr and references/katex.css inline.
Exit 0 printed or written, 2 an unknown widget or kind, or a missing file.
"""
import html
import pathlib
import re
import sys

REFS = pathlib.Path(__file__).resolve().parents[1] / "references"
BLOCK = re.compile(r"<style[^>]*>.*?</style>\s*|<script>.*?</script>\s*", re.S)
# spec lines on what a widget's script does, not on what the author writes
SCRIPTED = ("focus", "legend", "keyboard", "screen reader")
# widgets whose spec is their whole comment and body, as against the diagram's kinds
WHOLE = ("chart", "filter", "controls", "source")
# KaTeX's version pinned with references/katex.css's; an Artifact page loads only scripts from jsdelivr, so its style is inline
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.18.9/dist/"
TEX = re.compile(r"\\[(\[]")


def unit(name):
    """(its spec comment, its style and script blocks, its body templates) of references/<name>.html."""
    text = (REFS / f"{name}.html").read_text()
    comment = re.match(r"<!--.*?-->", text, re.S).group(0)
    rest = text[len(comment):]
    return comment, [b.strip() for b in BLOCK.findall(rest)], BLOCK.sub("", rest).strip()


def kinds():
    """{diagram kind: its section template}."""
    sections = re.split(r"\n(?=<section)", unit("diagram")[2])
    return {re.search(r'data-diagram="([\w-]+)"', s).group(1): s for s in sections}


def spec(widget):
    """A widget's spec comment and body template, unindented, with no style or script; a diagram kind's alone."""
    if widget == "page" or widget in WHOLE:
        comment, _, body = unit(widget)
        if widget == "page":
            body = re.search(r"<main>.*?</main>", body, re.S).group(0)
    else:
        comment, body = unit("diagram")[0], kinds()[widget]
        key = lambda line: (re.match(r"\s*([a-z][\w -]*): ", line) or [None, None])[1]
        drop = set(kinds()) - {widget} | set(SCRIPTED)
        comment = "\n".join(line for line in comment.splitlines() if key(line) not in drop)
    return comment + "\n" + re.sub(r"(?m)^[ \t]+", "", body) + "\n"


def assemble(body):
    """The whole page: the shell titled by the body's h1, each used widget's style and script once."""
    body = re.sub(r"^\s*<main>|</main>\s*$", "", body).strip()
    used = list(dict.fromkeys(re.findall(r'data-widget="([^"]*)"', body)))
    for w in used:
        if w not in (*WHOLE, "diagram"):
            raise LookupError(f"unknown widget {w!r}; widgets: {', '.join(WHOLE)}, diagram")
    for k in dict.fromkeys(re.findall(r'data-diagram="([^"]*)"', body)):
        if k not in kinds():
            raise LookupError(f"unknown diagram kind {k!r}; kinds: {', '.join(kinds())}")
    _, blocks, shell = unit("page")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = html.escape(html.unescape(re.sub(r"<[^>]+>|\s+", " ", h1.group(1)).strip())) if h1 else ""
    own = [b for w in used for b in unit(w)[1]]
    styles = [b for b in blocks + own if b.startswith("<style")]
    scripts = [b for b in blocks + own if b.startswith("<script")]
    if TEX.search(re.sub(r"<(code|pre)\b.*?</\1>", "", body, flags=re.S)):
        styles.append('<style id="math">\n' + (REFS / "katex.css").read_text().strip() + "\n</style>")
        scripts[:0] = [f'<script src="{KATEX}{f}"></script>' for f in ("katex.min.js", "contrib/auto-render.min.js")]
    head, _, _ = shell.partition("<main>")
    return (head.replace("{{title}}", title).rstrip() + "\n" + "\n".join(styles) + "\n<main>\n" + body + "\n</main>\n"
            + "\n".join(scripts) + "\n</html>\n")


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--spec":
        if args[1] not in ("page", *WHOLE, *kinds()):
            print(f"assemble.py: unknown widget {args[1]!r}; widgets: page, {', '.join((*WHOLE, *kinds()))}", file=sys.stderr)
            return 2
        sys.stdout.write(spec(args[1]))
        return 0
    if len(args) != 2 or args[0].startswith("-"):
        print("usage: assemble.py --spec <widget> | assemble.py <body.html> <page.html>", file=sys.stderr)
        return 2
    body = pathlib.Path(args[0])
    if not body.is_file():
        print(f"assemble.py: no file {body}", file=sys.stderr)
        return 2
    try:
        page = assemble(body.read_text())
    except LookupError as e:
        print(f"assemble.py: {e.args[0]}", file=sys.stderr)
        return 2
    pathlib.Path(args[1]).write_text(page)
    print(args[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
