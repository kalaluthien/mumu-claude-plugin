# Artifact page

## Composition

- A page is one HTML file that opens from `file://`: one `<style>` holding
  [skin.css](artifact/shared/skin.css) verbatim, then `<main>` with the `h1`, a `p.read` of the one thing to read off the page, the widgets in
  move order, and a `footer` citing the source at a sha. With 4 or more
  `h2`s, or chapters, a `nav` after `p.read` links each `h2` by its id; with
  fewer, none.
- Content that nests, parts that each hold sections of their own, is read a
  chapter at a time: each part is an `h2` with its sections as `h3`s, the two
  in one `<section data-chapter>`, and
  [chapters](artifact/shared/chapters.html) is copied once after the widgets.
  Content with no such parts stays one scroll, with no `h3`.
- Links tie the page together: each `h2` and `h3` has an id, and a sentence
  that names another section links its heading. A key term is defined once,
  as `<dfn id="t-<term>">` where it first appears, and its later mentions
  link there, `<a href="#t-<term>">`, one link per paragraph.
- Each widget is its file in [widgets/](artifact/widgets/), copied whole, its
  spec comment followed then deleted, every `{{...}}` filled or its element
  deleted; its `<style>` and `<script>` once per page, `{{id}}` unique per
  copy. A figure over 9 boxes is two figures.
- A widget that plays its steps names its part, copied once per page after
  the widgets: [slide](artifact/shared/slide.html) changes one stage in place
  (the reader compares the same marks), [swipe](artifact/shared/swipe.html)
  is a strip of cards (each step a separate moment).

## Base skills

Load `artifact-design` before writing the page, directly, not through the
`Artifact` tool's `quickstart`, since the page is a plain HTML file; load
`artifact-diagramming` before filling a `diagram` widget. Where they disagree
with this skill, this skill overrides them:

- The skin and widgets are the page's whole design, overriding
  `artifact-design`'s design plan and editorial process: no palette, typeface
  or value of the page's own.
- `<html lang="ko">` overrides `artifact-design`'s skeleton rule of no
  `<html>` tag, since `check.py` reads the `lang`.
- Data is drawn by the `chart` widget alone, overriding `artifact-design`'s
  rule to load a charting library.
- The Check loop below overrides `artifact-design`'s "Write, look once,
  publish": rerun `check.py` until it prints `pass`.
- A widget's anatomy overrides `artifact-diagramming`'s Inline SVG mechanics:
  its sizes, markers, `<title>` and `<desc>`, and a key in the `figcaption`.

## Korean

The hard rule in `SKILL.md` covers every visible word, a widget's fixed words
and each control included. A heading stays a noun phrase: 작업 큐의 구조, not
작업 큐는 세 파일이에요. A sentence reads as a Korean speaker would say it:
subject and verb plain, no English word order, no stacked nouns, no borrowed
metaphor (스타일을 품어요 → 스타일을 파일 안에 담고 있어요).

## Delivery

`<slug>.html`, named for its topic, in the session's scratch directory,
published with the `Artifact` tool, else opened with `open`.

## Check

`"${CLAUDE_PLUGIN_ROOT}/scripts/page/check.py" <page>` loads it at 320 px
with and without motion, clicks each control, reads its Korean, `nav` and
`#` links, checks each chart against its table, and in real time swipes each
strip and opens each chapter by its `nav`, pager, `#<id>` and back; fix
each `FAIL` line and rerun until the
last line is `pass`; exit 2 says why it could not run.
