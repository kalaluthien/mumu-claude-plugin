# Artifact page

## Composition

- A page is one HTML file that opens from `file://`: `<title>`, one `<style>`
  holding [skin.css](artifact/shared/skin.css) verbatim, then `<main>` with
  the `h1`, a `p.read` of the one thing to read off the page, the widgets in
  move order, and a `footer` citing the source at a sha. With 4 or more
  `h2`s, a `nav` after `p.read` links each by its id; with fewer, none.
- Each widget is its file in [widgets/](artifact/widgets/), copied whole, its
  spec comment followed then deleted, every `{{...}}` filled or its element
  deleted; its `<style>` and `<script>` once per page, `{{id}}` unique per
  copy. A figure over 9 boxes is two figures.
- A widget that plays its steps names its part, copied once per page after
  the widgets: [slide](artifact/shared/slide.html) changes one stage in place
  (the reader compares the same marks), [swipe](artifact/shared/swipe.html)
  is a strip of cards (each step a separate moment).
- The skin and widgets are the page's whole design: no values of its own, and
  no `quickstart`, `artifact-design`, `artifact-capabilities` or `dataviz`
  before the `Artifact` call, which only publishes the file.

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
with and without motion, clicks each control, reads its Korean and `nav` and
checks each chart against its table and swipes each strip in real time; fix
each `FAIL` line and rerun until the
last line is `pass`; exit 2 says why it could not run.
