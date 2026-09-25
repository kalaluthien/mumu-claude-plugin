---
name: writing-documents
description: Use before writing a document a person will read outside the chat - a GitHub issue or pull request body or comment, an Artifact page, a repository page (README, docs) - to explain, draw, map, walk through, compare or report something, even when only the content was asked for. Not for a plain chat answer, nor for code or its comments, nor for asking the user open questions (that is `grill-me`).
user-invocable: false
---

# writing-documents

**Goal**: the reader gets what they need, in the order they need it, in the
form that shows it best, and can act on it. A format the running skill or the
repository states wins: its template, headings, comment kinds. The topic is
the one named, else the conversation's.

## Doctypes

The reader's situation picks the doctype; its moves, in order, are the
document's parts. The outermost purpose is the doctype, the others nest as
its moves; a move with nothing to say is dropped.

| doctype | the reader | moves, in order |
| --- | --- | --- |
| `proposal` | must agree to what is not settled: a plan, a design, an issue, a choice | **plan**: the goal and when it is done · **narrative and comparison**: why, and the options against one set of criteria, fixed before any option · **settled answers**: what `grill-me` settled with the reader · **decide**: the recommendation and the fact that would change it |
| `textbook` | must understand or use what is settled: a system, a change, a result | **explain**: what it is made of and how it works · **teach**: one claim per section, with its reason and evidence · **guide**: the steps the reader takes, each with its check · **report**: what was done, its evidence, the next action |

## Mapping

The content picks the widget, one rule per row; a new rule is a new row
naming a file in `references/page/widgets/`, and `scripts/skill/skill-check.py`
fails on any other. `scripts/page/gallery.py` renders every widget in every
state, light and dark. A figure on GitHub or a repository page is an SVG
image, exported by [github.md](references/github.md).

| when the content is | widget | in markdown |
| --- | --- | --- |
| a software system's structure: files, modules, their roles | `file-tree`, first on the page | a code-block tree, one comment per line |
| who calls the system and what it calls: actors, entry points, boundaries | `system-context` | its SVG |
| behaviour: what happens in one use case | `use-case`, one per use case | its SVG, then a numbered list of calls |
| a sequence the reader follows one step at a time: a request travelling the system | `use-case`, played | a numbered list, one step and its reason each |
| a structure before and after a change: what it adds, modifies and removes | `before-after` | a diff of the tree |
| states and the events that move between them: a job's life, a connection | `state-machine` | its SVG, then a table of state, event, next state |
| rows sharing columns: options, findings, done-criteria | `table` | a table |
| two dimensions crossed, one mark per cell: options against criteria, roles against permissions | `matrix` | a table, a symbol per cell and its key |
| many items the reader narrows or reorders by their attributes | `filter` | a table sorted by the key that matters most |
| a result the reader should see as it is: a page, a screen, an email | `preview` | an image of it |
| steps the reader carries out one at a time, each done before the next | `stepwise` | a numbered list, each step with its check |
| a term the reader may not know, used where the prose must not stop for it | `hint` | the term with its meaning in parentheses, once |
| a claim with its reason and evidence (code, or the hunk that changed) | `section` | a heading over paragraphs; a hunk as a `diff` code block |

## Routing

Where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`; then read the one file for that place and follow it.

| the document goes to | read |
| --- | --- |
| a GitHub issue, pull request, or a comment on one | [github.md](references/github.md) |
| an Artifact page | [page.md](references/page.md) |
| a repository page: a README, a file under `docs/` | [repository.md](references/repository.md) |

Delivered anywhere, give the one-sentence version in chat.

## Writing

- Name things instead of counting them: a count goes stale, a name can be
  grepped. A heading is a noun phrase naming its part; the claim goes in the
  first sentence under it.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells. A change you judge wrong is
  said so, plainly.
- A step caption names one change and its effect, never what the figure
  shows.

## Done when

- A part no fact settles goes to `grill-me` by name, and the document carries
  only its settled answers; nothing is written before.
- Reread for order, each claim against its evidence, cuts and register.
- The checks the routed file names print `pass`.
- A rejected draft is edited only after a reader, an editor and a hostile
  fact-checker each say why it fails.
