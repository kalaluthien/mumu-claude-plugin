---
name: writing-documents
description: Use before writing anything a person will read - a chat answer, a GitHub issue or pull request body or comment, an Artifact page, a repository page - to explain, draw, map, walk through, compare or report something, or say what the facts imply (so what), and before asking the user to settle a decision, proposal or plan with open choices (grill me), even when only the content was asked for. Not for code or its comments.
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
| `proposal` | must agree to what is not settled: a plan, a design, an issue, a choice | **plan**: the goal and when it is done · **narrative and comparison**: why, and the options against one set of criteria, fixed before any option · **interactive form**: the questions only the reader can settle · **decide**: the recommendation and the fact that would change it |
| `textbook` | must understand or use what is settled: a system, a change, a result | **explain**: what it is made of and how it works · **teach**: one claim per section, with its reason and evidence · **guide**: the steps the reader takes, each with its check · **report**: what was done, its evidence, the next action |

Asked only what follows from facts on screen, there is no doctype: say what
they imply, then the one action recommended, or plainly that none follows.

## Mapping

The content picks the widget, one rule per row; a new rule is a new row
naming a file in `widgets/`, and `bin/skill-check.py` fails on any other.
`bin/gallery.py` renders every widget in every state, light and dark.

| when the content is | widget | in markdown |
| --- | --- | --- |
| a software system's structure: files, modules, their roles | `file-tree`, first on the page | a code-block tree, one comment per line |
| who calls the system and what it calls: actors, entry points, boundaries | `context` | Mermaid `flowchart` on GitHub, a text sketch in chat |
| behaviour: what happens in one use case | `flow`, one per use case | a numbered list of calls; Mermaid `sequenceDiagram` on GitHub |
| a sequence the reader follows one step at a time: a request travelling the system | `flow`, played | a numbered list, one step and its reason each |
| a structure before and after a change: what it adds and removes | `change` | a diff of the tree |
| rows sharing columns: options, findings, done-criteria | `table` | a table |
| questions only the reader can settle | `round` | by [Rounds](#rounds) |
| a claim with its reason and evidence (code, or the hunk that changed), or steps with their checks | `section` | a heading over paragraphs or a numbered list; a hunk as a `diff` code block |

## Composition

- A page is one HTML file that opens from `file://`: `<title>`, one `<style>`
  holding [skin.css](skin.css) verbatim, then `<main>` with the `h1`, a
  `p.read` of the one thing to read off the page, the widgets in move order,
  and a `footer` citing the source at a sha. Nothing fetched.
- Each widget is its file in `widgets/`, copied whole, its spec comment
  followed then deleted, every `{{...}}` filled or its element deleted; a
  widget's `<style>` and `<script>` once per page however many copies;
  `{{id}}` unique per copy, so inline SVG ids never collide. A played `flow`
  or a `change` also needs [player.html](player.html) once, verbatim;
  `data-player="scroll"` drives it by scrolling instead of buttons. A figure
  over 9 boxes is two figures.
- The skin is the design system: primitives, semantic tokens (colour roles,
  diagram palette, type, space, line, radius, layout, motion) and each
  widget's own tokens; a page adds none of its own values. The accent marks
  links, focus and the current step only.
- Markdown (chat, GitHub, any agent): the moves as headings, each widget as
  its markdown column; Mermaid only on GitHub.
- The skin and widgets are a page's only design rules: before the `Artifact`
  call, do not run its `quickstart` or load `artifact-design` or
  `artifact-capabilities`; the tool only publishes the file.

## Writing

- Name things instead of counting them: a count goes stale, a name can be
  grepped. A heading says what is true, as a sentence.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells. A change you judge wrong is
  said so, plainly.
- A step caption names one change and its effect, never what the figure
  shows.
- An Artifact page is Korean, always: `<html lang="ko">`; every visible word
  in Korean - headings, prose, captions, figure labels, alt text and
  each control, a widget's fixed words included; the polite `-요` or `-니다`,
  never a plain `-다`, in everyday words. English only inside `<code>` or as a
  name or path; a technical term once as Korean with the English in
  parentheses, as 큐(queue).

## Rounds

- A question waits while one it rests on is open, as a definition of done
  waits on its scope. Each round asks every open question whose
  prerequisites are settled, numbered `Q1`, `Q2`, each with `Recommended:`
  and your answer; then wait.
- Facts are yours to find; a pending lookup holds back only the questions
  under it. Attack each answer once before writing it: a counterexample, an
  edge case, a check that can fail, or a repository term that says otherwise.
- Four questions or fewer with `AskUserQuestion` in the session: ask there;
  more with the `Artifact` tool: a page with the `round` widget; else
  numbered text in chat.
- The pasted block's first line is `writing-documents: <target>, round <n>`,
  each `Qn:` with its answer indented under it. An answer equal to its
  recommendation accepts it, an empty one leaves it open, and a block that
  matches no round is said to match none.

## Delivery

Where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`:

- chat: markdown;
- GitHub issue or pull request: the body or a comment by the repository's
  procedure, else `gh issue create`. Unless that procedure sets the form, a
  body opens with one sentence on why, then the Mermaid figure of what the
  change alters, then the proof (each check and its result), then the files
  in reading order, each with its why; files with nothing to say share one
  closing line, and a misleading `+`/`-` count is called out. Each
  `path:line` links to the blob at the head sha;
- Artifact page: `<slug>.html` in the session's scratch directory, published
  with the `Artifact` tool, else opened with `open`;
- repository page: where the repository keeps pages, linked from its README,
  landed by its procedure.

Delivered elsewhere, give the one-sentence version in chat.

## Done when

- Every part no fact settles is settled by [Rounds](#rounds); nothing is
  acted on before.
- Reread for order, each claim against its evidence, cuts and register.
- A page: `"${CLAUDE_PLUGIN_ROOT}/bin/page-check.sh" <page>` loads it at
  320 px, clicks each control once, again with reduced motion, and prints
  `pass`; on `FAIL` fix and rerun; exit 2 says why it could not run. An
  Artifact page also passes `"${CLAUDE_PLUGIN_ROOT}/bin/korean-check.py" <page>`.
- A rejected draft is edited only after a reader, an editor and a hostile
  fact-checker each say why it fails.
