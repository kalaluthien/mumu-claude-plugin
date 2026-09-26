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
else is plain HTML the skin styles. The content picks the widget, one rule per
row; a new row names a file in `references/` and its kind, and
`scripts/skill-check.py` fails on any other. Data is drawn only by the `chart`
widget, with no chart library. On a page, `check.py` fails a skipped row: four
files or more named by path in `<code>` with no `file-tree`, or a flow drawn in
text with arrows (→, ▶) with no `use-case`.

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
`AskUserQuestion`. An Artifact page follows [artifact.md](references/artifact.md).
A GitHub issue, pull request or comment follows the repository's procedure,
else `gh issue create`; a repository page (a README, a doc) is linked from the
README and lands by a pull request. There the moves are headings, each widget
its markdown column above, and no Mermaid, since an SVG reads the same on every
client. Delivered anywhere, give the one-sentence version in chat.

## GitHub body

Unless the repository's procedure sets the form, a body is one sentence on why
the change exists, the figure of what it alters, the proof (each check run and
its result), then the files in reading order, each with its why; a misleading
line count is called out. A `path:line` links to the blob at the head sha,
or relatively on a repository page.

A figure is its widget drawn on a page by [artifact.md](references/artifact.md),
labels in English allowed, then written as SVG by `check.py <page> --svg <dir>`.
On GitHub, reference it as `![<alt>](./<page>-<n>.svg)` and pass
`--attach './<page>-<n>.svg#<alt>'` to `gh`; every later edit of the body
re-passes `--attach` for each figure, or the path stays local. On a repository
page, commit it beside the page.

## Writing

- Name things instead of counting them: a count goes stale, a name can be
  grepped. A heading is a noun phrase naming its part; the claim goes in the
  first sentence under it.
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

## Done when

- A part no fact settles goes to `grill-me` by name, and the document carries
  only its settled answers; nothing is written before.
- Reread for order, each claim against its evidence, cuts and register.
- An Artifact page: `"${CLAUDE_PLUGIN_ROOT}/skills/writing-documents/scripts/check.py" <page.html>` prints `pass` last.
- A rejected draft is edited only after a reader, an editor and a hostile
  fact-checker each say why it fails.
