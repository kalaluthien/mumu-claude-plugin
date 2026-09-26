#!/usr/bin/env python3
"""Write the design system's gallery: every widget in every state, light and dark.

usage: gallery.py <out.html> [skill dir], default the skill this script sits in.
Each copy sits in a .theme-light or .theme-dark box with data-state set, which the skin and
the widgets read to force that state. A widget shows each template section in every state; a
widget with fixtures beside this script (<widget>-fixtures.html, filled copies) shows each fixture
by default and the first in every state. Open adds `open` to each <details> and shows what is
hidden; disabled adds `disabled` to each control. The shared parts come once, their scripts
last. The page is Korean: a control's label takes its Korean from KOREAN, and every other
placeholder reads 예시 (example).
"""
import pathlib
import re
import sys

MODES = ("light", "dark")
STATES = ("default", "hover", "focus", "open", "disabled")
KOREAN = {
    "Back|Next": "뒤로|다음",
    "gone": "삭제", "changed": "변경", "new": "추가", "Data table": "데이터 표",
}
NAMES = {"default": "기본", "hover": "올림", "focus": "초점", "open": "펼침", "disabled": "꺼짐",
         "light": "밝은 테마", "dark": "어두운 테마"}


def parts(html):
    """(style and script blocks, body) of a unit, its spec comment dropped."""
    html = re.sub(r"^<!--.*?-->\s*", "", html, count=1, flags=re.S)
    blocks = re.findall(r"<style>.*?</style>|<script>.*?</script>", html, re.S)
    body = re.sub(r"<style>.*?</style>\s*|<script>.*?</script>\s*", "", html, flags=re.S)
    return blocks, body


def fill(body):
    return re.sub(r"\{\{([^}]*)\}\}", lambda m: KOREAN.get(m.group(1), "예시"), body)


def in_state(body, state):
    if state == "open":
        body = body.replace("<details>", "<details open>").replace(" hidden>", ">")
    if state == "disabled":
        body = re.sub(r"<(button|textarea|fieldset)\b", r"<\1 disabled", body)
    return body


def gallery(skill):
    page = skill / "references" / "artifact"
    skin = (page / "shared" / "skin.css").read_text()
    head, sections = [], []
    for f in sorted((page / "widgets").glob("*.html")):
        blocks, body = parts(f.read_text())
        head += blocks
        fixtures = pathlib.Path(__file__).with_name(f"{f.stem}-fixtures.html")
        if fixtures.exists():
            bodies, full = re.split(r"\n(?=<figure)", parts(fixtures.read_text())[1].strip()), 1
        else:
            bodies = re.split(r"\n(?=<section)", body.strip())
            full = len(bodies)
        copies = []
        for mode in MODES:
            for n, one in enumerate(bodies):
                for state in STATES if n < full else STATES[:1]:
                    uid = f"{f.stem}-{mode}-{state}-{n}"
                    copies.append(f'<div class="theme-{mode}" data-state="{state}">\n'
                                  f'<p class="muted"><code>{f.stem}</code> · {NAMES[state]} · {NAMES[mode]}</p>\n'
                                  f'{fill(in_state(one.replace("{{id}}", uid), state))}</div>')
        sections.append(f'<section aria-labelledby="g-{f.stem}">\n<h2 id="g-{f.stem}"><code>{f.stem}</code></h2>\n'
                        + "\n".join(copies) + "\n</section>")
    for f in sorted((page / "shared").glob("*.html")):
        head += parts(f.read_text())[0]
    styles = [b for b in head if b.startswith("<style>")]
    scripts = [b for b in head if b.startswith("<script>")]
    return ("<!doctype html>\n<html lang=\"ko\">\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>위젯 모음</title>\n<style>\n" + skin
            + ".theme-light, .theme-dark { padding: var(--sp-3); margin: var(--sp-4) 0; border: var(--line) solid var(--border); }\n"
            + "</style>\n" + "\n".join(styles)
            + "\n<main>\n<h1>위젯 모음</h1>\n<p class=\"read\"><code>writing-documents</code>의 모든 위젯을 모든 상태로, 밝은 테마와 어두운 테마에서 보여 줍니다.</p>\n"
            + contents("\n".join(sections)) + "\n".join(sections) + "\n</main>\n" + "\n".join(scripts) + "\n</html>\n")


def contents(body):
    """The page's <nav>: a link to each <h2> by its id, as artifact.md's Composition asks."""
    links = "".join(f'<li><a href="#{i}">{re.sub(r"<[^>]+>", "", text).strip()}</a></li>'
                    for i, text in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.S))
    return f"<nav><ol>{links}</ol></nav>\n"


def main():
    skill = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else \
        pathlib.Path(__file__).resolve().parents[1]
    pathlib.Path(sys.argv[1]).write_text(gallery(skill))
    return 0


if __name__ == "__main__":
    sys.exit(main())
