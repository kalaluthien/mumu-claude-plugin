---
name: writing-documents
description: Use before writing a document a person will read outside the chat - a GitHub issue or pull request body or comment, an Artifact page, a repository page (README, docs) - to explain, draw, chart data, map, walk through, compare or report something, even when only the content or a chart was asked for; a chart on such a page is drawn here, not by `dataviz`. Not for a plain chat answer, nor for code or its comments, nor for asking the user open questions (that is `grill-me`).
user-invocable: false
---

# writing-documents

**Goal**: the reader gets what they need, in the order they need it, in the
form that shows it best, and can act on it. A format the running skill or the
repository states wins: its template, headings, comment kinds; a design or
chart skill such as `dataviz` does not, since the skin and widgets here are
the page's whole design. The topic is the one named, else the conversation's.

## Doctypes

The reader's situation picks the doctype; its moves, in order, are the
document's parts. The outermost purpose is the doctype, the others nest as
its moves; a move with nothing to say is dropped.

| doctype | the reader | moves, in order |
| --- | --- | --- |
| `proposal` | must agree to what is not settled: a plan, a design, an issue, a choice | **plan**: the goal and when it is done · **narrative and comparison**: why, and the options against one set of criteria, fixed before any option · **settled answers**: what `grill-me` settled with the reader · **decide**: the recommendation and the fact that would change it |
| `textbook` | must understand or use what is settled: a system, a change, a result | **explain**: what it is made of, how it works and the traps a user hits · **teach**: one claim per section, with its reason and evidence · **guide**: the steps the reader takes, each with its check · **report**: what was done, its evidence, the next action |

## Mapping

A widget exists only where this skill tuned, combined or made one; everything
else is plain HTML the skin styles: headings over paragraphs, lists, a
`<table>`, evidence in `<details>`, code in `<pre>`. The content picks
the widget, one rule per row; a new rule is a new row naming a file in
`references/artifact/widgets/` and, for `diagram` and `chart`, its kind, and
`scripts/skill/skill-check.py` fails on any other. Data is drawn only by the
`chart` widget, with no chart library. `scripts/skill/gallery.py` renders
every widget in every state, light and dark. A figure in markdown is an SVG
image, exported by [markdown.md](references/markdown.md).

| when the content is | widget | in markdown |
| --- | --- | --- |
| a software system's structure: files, modules, their roles | `diagram` `file-tree`, first on the page | a code-block tree, one comment per line |
| a structure before and after a change: what it adds, modifies and removes | `diagram` `file-tree`, slid | a diff of the tree |
| who calls the system and what it calls: actors, entry points, boundaries | `diagram` `system-context` | its SVG |
| behaviour: what happens in one use case; swiped, a request the reader follows call by call | `diagram` `use-case`, one per use case | its SVG, then a numbered list of calls |
| values compared across categories: which is largest, by how much | `chart` `bar` | its SVG, then the table |
| change over time: a trend, a rise, a fall | `chart` `line` | its SVG, then the table |

## Routing

Where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`; then read the one file for that place and follow it.

| the document goes to | read |
| --- | --- |
| a GitHub issue, pull request or comment; a repository page: a README, `docs/` | [markdown.md](references/markdown.md) |
| an Artifact page | [artifact.md](references/artifact.md) |

Delivered anywhere, give the one-sentence version in chat.

## Writing

- Name things instead of counting them: a count goes stale, a name can be
  grepped. A heading is a noun phrase naming its part; the claim goes in the
  first sentence under it.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells. A change you judge wrong is
  said so, plainly; a reason the source omits is called absent, not guessed.
- A step caption names one change and its effect, never what the figure
  shows.
- An Artifact page is Korean, a hard rule: `<html lang="ko">`, and every
  visible word Korean, in the polite `-요` or `-니다`, never a plain `-다`,
  and in everyday words. English stays only inside `<code>` or as a name or
  path; a technical term appears once as Korean with the English in
  parentheses, as 큐(queue).

## Done when

- A part no fact settles goes to `grill-me` by name, and the document carries
  only its settled answers; nothing is written before.
- Reread for order, each claim against its evidence, cuts and register.
- The checks the routed file names print `pass`.
- An Artifact page: `"${CLAUDE_PLUGIN_ROOT}/scripts/page/check.py" <page.html>` prints one line per check, then `pass` or `FAIL`.
- A rejected draft is edited only after a reader, an editor and a hostile
  fact-checker each say why it fails.
