#!/usr/bin/env python3
"""Write the design system's gallery: every widget in every state, light and dark.

usage: gallery.py <out.html> [skill dir], default the writing-documents skill beside this script.
Each copy sits in a .theme-light or .theme-dark box with data-state set, which the skin and
the widgets read to force that state; open adds `open` to each <details> and shows a round's
answer block, disabled adds `disabled` to each control. The page is Korean, as every Artifact
page is: a control's label takes its Korean from KOREAN, a round's number is 1, and every other
placeholder reads 예시 (example).
"""
import pathlib
import re
import sys

MODES = ("light", "dark")
STATES = ("default", "hover", "focus", "open", "disabled")
KOREAN = {
    "Back|Play|Pause|Next|Step": "뒤로|재생|멈춤|다음|단계",
    "gone": "삭제", "changed": "변경", "new": "추가", "Recommended": "추천", "Answer": "답", "Answer block": "답 블록",
    "Build the answer block": "답 블록 만들기", "Evidence": "근거", "Bold": "굵은 글씨", "n": "1",
    "Copied: paste it into the chat": "복사했어요. 채팅에 붙여 넣으세요.",
    "Selected: copy it and paste it into the chat": "선택했어요. 복사해서 채팅에 붙여 넣으세요.",
    "high": "높음", "mid": "보통", "low": "낮음", "none": "없음", "Key": "범례",
    "done": "완료", "Done, next step": "완료, 다음 단계",
    "%n of %total shown": "전체 %total개 중 %n개", "Filter and sort": "거르기와 정렬", "Search": "검색",
    "Sort": "정렬", "Written order": "쓴 순서", "Name": "이름", "Clear all": "모두 지우기",
    "No item matches; clear a filter": "맞는 항목이 없어요. 조건을 하나 지워 보세요.",
    "Open at full size": "크게 보기", "Close": "닫기",
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
    page = skill / "references" / "page"
    skin = (page / "skin.css").read_text()
    head, sections = [], []
    for f in sorted((page / "widgets").glob("*.html")):
        blocks, body = parts(f.read_text())
        head += blocks
        copies = []
        for mode in MODES:
            for state in STATES:
                uid = f"{f.stem}-{mode}-{state}"
                copies.append(f'<div class="theme-{mode}" data-state="{state}">\n'
                              f'<p class="muted"><code>{f.stem}</code> · {NAMES[state]} · {NAMES[mode]}</p>\n'
                              f'{fill(in_state(body.replace("{{id}}", uid), state))}</div>')
        sections.append(f'<section aria-labelledby="g-{f.stem}">\n<h2 id="g-{f.stem}"><code>{f.stem}</code></h2>\n'
                        + "\n".join(copies) + "\n</section>")
    styles = [b for b in head if b.startswith("<style>")]
    scripts = [b for b in head if b.startswith("<script>")]
    return ("<!doctype html>\n<html lang=\"ko\">\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>위젯 모음</title>\n<style>\n" + skin
            + ".theme-light, .theme-dark { padding: var(--sp-3); margin: var(--sp-4) 0; border: var(--line) solid var(--border); }\n"
            + "</style>\n" + "\n".join(styles)
            + "\n<main>\n<h1>위젯 모음</h1>\n<p class=\"read\"><code>writing-documents</code>의 모든 위젯을 모든 상태로, 밝은 테마와 어두운 테마에서 보여 줍니다.</p>\n"
            + "\n".join(sections) + "\n</main>\n" + "\n".join(scripts) + "\n</html>\n")


def main():
    skill = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else \
        pathlib.Path(__file__).resolve().parents[2] / "skills" / "writing-documents"
    pathlib.Path(sys.argv[1]).write_text(gallery(skill))
    return 0


if __name__ == "__main__":
    sys.exit(main())
