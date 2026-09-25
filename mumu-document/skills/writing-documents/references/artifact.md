# Artifact page

## Composition

- A page is one HTML file that opens from `file://`: `<title>`, one `<style>`
  holding [skin.css](artifact/skin.css) verbatim, then `<main>` with the `h1`, a
  `p.read` of the one thing to read off the page, the widgets in move order,
  and a `footer` citing the source at a sha. Nothing fetched but the skin's
  fonts, which fall back to installed faces offline.
- Each widget is its file in [widgets/](artifact/widgets/), copied whole, its spec
  comment followed then deleted, every `{{...}}` filled or its element
  deleted. A widget carries its own `<style>` and `<script>`: once per page
  however many copies; `{{id}}` unique per copy, so inline SVG ids never
  collide. A figure over 9 boxes is two figures.
- The skin is the design system of [design.md](artifact/design.md), an
  editorial black on white: primitives, semantic tokens (colour roles,
  diagram palette, type, space, line, radius, layout, motion); each widget
  defines its own tokens. A page adds no values of its own. Links take
  `--link`; the ink accent marks focus, hover and the current step only.
- The skin and widgets are a page's only design rules: before the `Artifact`
  call, do not run its `quickstart` or load `artifact-design` or
  `artifact-capabilities`; the tool only publishes the file.

## Korean

An Artifact page is Korean, always: `<html lang="ko">`; every visible word in
Korean - headings, prose, captions, figure labels, alt text and each control,
a widget's fixed words included; the polite `-요` or `-니다`, never a plain
`-다`, in everyday words. English only inside `<code>` or as a name or path; a
technical term once as Korean with the English in parentheses, as 큐(queue).
A heading stays a noun phrase: 작업 큐의 구조, not 작업 큐는 세 파일이에요.
A sentence reads as a Korean speaker would say it: one idea, its subject and
verb plain, no English word order, no stacked nouns and no borrowed metaphor
(스타일을 품어요 → 스타일을 파일 안에 담고 있어요).

## Delivery

`<slug>.html`, named for its topic, in the session's scratch directory,
published with the `Artifact` tool, else opened with `open`.

## Checks

- `"${CLAUDE_PLUGIN_ROOT}/scripts/artifact/artifact-check.sh" <page>` loads it at
  320 px, taps each hint, clicks each control once, again with reduced
  motion, and prints `pass`; on `FAIL` fix and rerun; exit 2 says why it could
  not run.
- `"${CLAUDE_PLUGIN_ROOT}/scripts/korean/korean-check.py" <page>` prints
  `pass`: Korean text, polite endings, noun-phrase headings.
