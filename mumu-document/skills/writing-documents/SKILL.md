---
name: writing-documents
description: Use before writing any document, page or diagram a person will read - explain, draw, map, walk through, compare, report, an issue or pull request body, what the facts imply (so what) - or before asking the user to settle a decision, proposal or plan with open choices (grill me), even when only the content was asked for. Not for code or its comments.
---

# writing-documents

Write the document by [doctype.md](references/doctype.md); read it first. A
format the running skill or the repository states wins over it: its
template, its headings, its comment kinds. The topic is the one named, else the conversation's.

1. **Doctype**: the question picks it; build its parts in order. Asked only
   what follows, answer as `doctype.md` says, with no doctype.
2. **Blanks**: a part no fact settles is the user's; settle every blank by
   [Rounds](#rounds) before delivering, and act on nothing before that.
3. **Medium**: markdown in one of its forms, or a page from
   [page.html](assets/page.html), whose `#round` form asks a round of
   questions.
4. **Plan** a page or a figure: one line naming the doctype, each figure
   with the paragraph beside it; then write.
5. **Check** a page: `"${CLAUDE_PLUGIN_ROOT}/bin/page-check.sh" <page>` clicks
   each control once and prints `pass`; on `FAIL`, fix and rerun; exit 2 says
   why it could not run.
6. **Deliver** by [Delivery](#delivery).

## Page rules over the Artifact tool

`page.html` and `doctype.md` are the page's only design rules: read
`page.html` before any `Artifact` call, and do not run its `quickstart` or
load `artifact-design` or `artifact-capabilities`. The `Artifact` tool only
publishes the finished file.

## Rounds

- A question waits while one it rests on is open, as a definition of done
  waits on its scope; the **frontier** is every question whose prerequisites
  are settled.
- Each round asks the whole frontier, numbered `Q1`, `Q2`, each with
  `Recommended:` and your answer under it; then wait.
- Facts are yours to find; a pending lookup holds back only the questions
  under it.
- Attack each answer once before writing it: a counterexample, an edge case,
  a check that can fail, or a term or code of the repository that says
  otherwise. Write it once it survives, or once the user restates it knowing
  the attack.
- Done when every blank is filled and the user confirms the document.

| the round | where |
| --- | --- |
| four questions or fewer, with `AskUserQuestion` in the session | `AskUserQuestion` |
| more, with the `Artifact` tool in the session | a page of questions in the `#round` form, recommendations prefilled |
| otherwise | numbered text in chat |

The form writes nowhere: it builds a block the user pastes back, its first
line `writing-documents: <target>, round <n>`, then each `Qn:` with the
answer indented two spaces under it. An answer equal to its recommendation
accepts it, an empty one leaves the question open, and a block that matches
no round is said to match none.

## Delivery

Where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`:

- chat: markdown;
- GitHub issue: the body or a comment by the repository's procedure, else
  `gh issue create`;
- page: `<slug>.html` in the session's scratch directory, published with the
  `Artifact` tool, else opened with `open`;
- repository page: where the repository keeps pages, linked from its README,
  landed by its procedure.

Delivered elsewhere, give the one-sentence version in chat.
