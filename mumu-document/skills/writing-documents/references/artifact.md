# Artifact page

## Composition

A page is one HTML file that opens from disk, copied from
[page.html](page.html), its comment followed then deleted: what goes in the
page, how chapters nest and how a widget plays its steps. Content whose parts each hold sections
is read a chapter at a time; content with none stays one scroll, with no `h3`.
Each `h2` and `h3` has an id, and a sentence that names another section links
it. A key term is defined once, as `<dfn id="t-<term>">` where it first
appears, and its later mentions link there, once a paragraph.

A widget is the part of [chart.html](chart.html) or [diagram.html](diagram.html)
the content needs, copied whole, its spec comment followed then deleted, every
`{{...}}` filled or its element deleted; its style and script once per page,
`{{id}}` unique per copy. A figure over 9 boxes is two figures.

## Base skills

This skill overrides `artifact-design`, `artifact-diagramming` and the
`Artifact` tool's `quickstart`: the skin and widgets are the whole design, with
no palette, typeface or chart library of the page's own; the page keeps
`<html lang="ko">`; `check.py` runs until `pass`, not a single look; a widget's
anatomy wins over their SVG mechanics.

## Korean

Every visible word is Korean, a widget's fixed words and each control
included, in the polite -요 or -니다, never a plain -다, and in everyday words.
English stays only inside `<code>` or as a name or path; a technical term
appears once as Korean with the English in parentheses, as 큐(queue). A heading
stays a noun phrase: 작업 큐의 구조, not 작업 큐는 세 파일이에요. A sentence reads
as a Korean speaker would say it: no English word order, no stacked nouns, no
borrowed metaphor (스타일을 품어요 → 스타일을 파일 안에 담고 있어요).

## Delivery and check

`<slug>.html`, named for its topic, in the session's scratch directory,
published with the `Artifact` tool, else opened locally.
`"${CLAUDE_PLUGIN_ROOT}/skills/writing-documents/scripts/check.py" <page>` loads
it at 320 px with and without motion, clicks each control, reads its Korean,
contents and links, checks each chart against its table, and in real time
swipes each strip and opens each chapter by its nav, pager, link and back;
fix each `FAIL` line and rerun until the last line is `pass`; exit 2 says why
it could not run.
