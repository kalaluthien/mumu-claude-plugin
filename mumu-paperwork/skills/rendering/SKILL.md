---
name: rendering
description: Use before making a page a person reads outside the chat - an Artifact or HTML page: a proposal, a system or specification document, a textbook or other teaching material, a report - to explain, draw, chart data, map, walk through, compare or report something, even when only the content or a chart was asked for; a chart on such a page is drawn here, not by `dataviz`, and an Artifact page is designed here, so load this before the `Artifact` tool's `quickstart`, which it skips with `artifact-design` and `artifact-diagramming`. Not for markdown on an issue tracker or in a repository (that is `writing`), nor for a plain chat answer, nor for code or its comments, nor for asking the user open questions (that is `grill-me`).
user-invocable: false
---

# rendering

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

## Composition

Before writing any section, the author settles the whole piece, in this order;
[rubric.md](references/rubric.md) grades it by the criteria each step names:

1. **Answer** (Pyramid and MECE, Narrative): the reader's question, what is at
   stake for them, and the answer in one sentence; that sentence opens the
   document, before the first heading (a page's `p.read`). It claims no more
   than the evidence below shows: a condition not yet measured stays in it.
2. **Outline** (Pyramid and MECE): the moves as headings, each a noun phrase
   that carries its section's claim (부산이 앞지른 요청, not 요청 수), so the
   headings read alone state the argument under the answer; siblings neither
   overlap nor leave a gap; a section with no claim is merged or cut.
3. **Order** (Narrative): overview to detail, each section answering the
   question the one before raises; time or step order only for a sequence;
   the reader's own exploration, such as a `filter` over every row, last.
4. **Form** (Emphasis, Coherence): each section the one form that carries its
   point: a sentence for a claim, a list for parallel items, a table for
   values compared across rows, a figure or widget by Mapping; space follows
   importance, and whatever does not prove the claim is cut. A figure's or
   table's caption says what to read off it, and the sentence before it
   names it. By default each concept the page explains gets a diagram,
   pseudocode of 3 lines at most (longer code is quoted as Writing says) or a
   worked example beside it where one fits, as in
   [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/):
   a figure between the paragraphs it serves, never a gallery at the end.
5. **Widgets**: at most 1 under each `h2` or `h3` and 5 on a page, of them at
   most 2 `filter` or `controls`, since most readers never touch a control and
   the claim stands in the text too; one sentence before a widget the reader
   drives says what to try; more is a second page.
6. **Ending**: the last section says what the reader does next, or that
   nothing is needed, and repeats no summary.

On a page, `check.py` fails the first rule and the widget limits.

## Mapping

A widget exists only where this skill tuned, combined or made one; everything
else is plain HTML the skin styles. The content picks the widget, one rule per
row; a new row names a file in `references/` and its kind, and
`scripts/skill-check.py` fails on any other. Data is drawn only by the `chart`
widget, with no chart library. On a page, `check.py` fails a skipped row: four
files or more named by path in `<code>` with no `file-tree`, or a flow drawn in
text with arrows (→, ▶) with no `use-case`.

| when the content is | widget |
| --- | --- |
| a software system's structure: files, modules, their roles | `diagram` `file-tree`, first on the page |
| a structure before and after a change: what it adds, modifies and removes | `diagram` `file-tree`, slid |
| who calls the system and what it calls: actors, entry points, boundaries | `diagram` `system-context` |
| behaviour: what happens in one use case: a request the reader follows call by call, in one still figure | `diagram` `use-case`, one per use case |
| things and the links between them: tasks and what blocks them, sessions and who waits on whom; what a node reaches | `diagram` `network`, 9 nodes at most |
| values compared across categories: which is largest, by how much | `chart` `bar` |
| change over time: a trend, a rise, a fall | `chart` `line` |
| many items the reader narrows to the few they need, by a tag or a word: rows, a list, cards | `filter` |
| a result that follows inputs the reader moves: a formula, a setting and its effect | `controls` |
| where a figure's, a table's or a claim's facts come from, and what they came through | `source`, under it |

## Routing

Where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`. An Artifact page skips the `Artifact` tool's `quickstart`,
`artifact-design` and `artifact-diagramming`: the skin and widgets are its
whole design, with no palette, typeface or chart library of its own. Its
author reads each widget's spec with
`"${CLAUDE_PLUGIN_ROOT}/skills/rendering/scripts/assemble.py" --spec <widget>`,
writes only the body, and `assemble.py <body> <page>` adds the skin and widget
code, as [artifact.md](references/artifact.md) says.
Markdown on an issue tracker or in a repository is `writing`'s; a figure it
needs is drawn here as a widget and written as SVG by `check.py <page> --svg
<dir>`. Delivered anywhere, give the one-sentence version in chat.

## Writing

- Name things instead of counting them: a count goes stale, a name can be
  grepped. A heading is a noun phrase carrying its part's claim, which the
  first sentence under it states.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells. A change you judge wrong is
  said so, plainly; a reason the source omits is called absent, not guessed.
- A step caption names one change and its effect, never what the figure
  shows.
- A table only when the reader compares values across rows; one record's
  fields are a `<dl>`, items with one attribute a list, items read one at a
  time with prose values an `h3` each. A table stays narrow: split it before
  adding a column, its first column the row's label; on a page it sits in the
  scroll box of [page.html](references/page.html)'s comment.
- A measurable quantity carries its unit: a time, a size, a count per time,
  money, a percent of what. In text beside the number; in a table header, in
  brackets, as 지연(ms), or in each cell; on a chart's axes and a diagram's
  labels. On a page, `check.py` fails a table column, a chart's included, of
  bare numbers with no unit in its header or cells.
- Code quoted on a page sits in `<figure class="code">`: a `<figcaption>`
  holding `<a href="…/blob/<sha>/<path>#L<a>-L<b>"><code><path>:<a>-<b></code></a>`,
  then `<pre><code>`, `<mark>` on each line that matters, one `⋯` line per
  cut; `check.py` fails a `pre` of 4 or more lines with no such caption.

## Done when

- A part no fact settles goes to `grill-me` by name, and the document carries
  only its settled answers; nothing is written before.
- Reread against Composition: the headings read alone state the argument,
  each section's first sentence is its point, and each figure is named in the
  sentence before it; the answer, a heading or a table cell never claims more
  than a later section allows; fix each miss.
- Reread for order, each claim against its evidence, cuts and register, then
  grade it against [rubric.md](references/rubric.md) and fix each criterion
  scored below 2.
- An Artifact page: `"${CLAUDE_PLUGIN_ROOT}/skills/rendering/scripts/check.py" <page.html>` prints `pass` last.
- A rejected draft is edited only after a reader, an editor and a hostile
  fact-checker each say why it fails.
