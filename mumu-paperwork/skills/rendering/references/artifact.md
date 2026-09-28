# Artifact page

## Structure

A page is one HTML file that opens from disk. Its author writes only the body,
what goes inside `<main>`, by `assemble.py --spec page`: what goes in the page,
how chapters nest and how a widget plays its steps. Content in parts, each with
two or more topics, is read a chapter at a time: a part is a
`<section data-chapter>`, a topic an `h3`. Content with no parts stays one
scroll, with no `h3`. Each `h2` and `h3` has an id, and a sentence that names another
section links it. A key term is defined once, as `<dfn id="t-<term>">` where it
first appears, and its later mentions link there, once a paragraph. A formula is
TeX in the prose, `\( … \)` inline and `\[ … \]` display, never an image or
Unicode look-alikes: `assemble.py` sets it in KaTeX's TeX fonts, and `check.py`
fails TeX left raw.

A widget is the template `assemble.py --spec <widget>` prints for the content's
kind (`chart`, `file-tree`, `system-context`, `use-case`, `network`, `filter`, `controls`, `source`), its spec followed,
every `{{...}}` filled or its element deleted, `{{id}}` unique per copy. A
figure over 9 boxes is two figures. Then
`"${CLAUDE_PLUGIN_ROOT}/skills/rendering/scripts/assemble.py" <body.html> <slug>.html`
writes the page: the skin, the `h1` as its title, and each widget's style and
script once. The page keeps `<html lang="ko">`; a hand-drawn `<svg>` outside a
widget fails `check.py`.

## Korean

Every visible word is Korean, a widget's fixed words and each control
included, in the formal -습니다/-ㅂ니다, never -요 or a plain -다, and in everyday words.
English stays only inside `<code>` or as a name or path; a technical term
appears once as Korean with the English in parentheses, as 큐(queue). A heading
stays a noun phrase: 작업 큐의 구조, not 작업 큐는 세 파일입니다. A sentence reads
as a Korean speaker would say it: no English word order, no stacked nouns, no
borrowed metaphor (스타일을 품습니다 → 스타일을 파일 안에 담고 있습니다).

## Delivery and check

`<slug>.html`, named for its topic, in the session's scratch directory,
published with the `Artifact` tool, else opened locally.
`"${CLAUDE_PLUGIN_ROOT}/skills/rendering/scripts/check.py" <page>` loads
it at 320 px with and without motion, clicks each control, reads its Korean,
contents and links, checks each chart against its table, and in real time
swipes each strip, opens each chapter by its nav, pager, link and back, and
fails a filter, controls or reading-aid control that changes nothing;
fix each `FAIL` line and rerun until the last line is `pass`; exit 2 says why
it could not run.
