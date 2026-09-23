---
name: grill-me
description: Use when the answer is still the user's to make - a decision, a proposal, a plan or an issue body with open choices to settle by asking them; not when the facts settle it (show-me) or code is under review.
---

# grill-me

Settle a document with the user: each blank in it is one question. The
document is the repository's template for the ask, found through its
`AGENTS.md` or `CLAUDE.md` and read now, else the doctype of
`${CLAUDE_PLUGIN_ROOT}/doctype.md` the question asks for.

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
- Done when every blank is filled and the user confirms the document; act on
  nothing before that. Then hand the document to `show-me` to deliver.

## Where a round is asked

| the round | where |
| --- | --- |
| four questions or fewer, with `AskUserQuestion` in the session | `AskUserQuestion` |
| more, with the `Artifact` tool in the session | the `#round` form of `${CLAUDE_PLUGIN_ROOT}/page.html`, recommendations prefilled, checked and delivered as `show-me` delivers a page |
| otherwise | numbered text in chat |

The form writes nowhere: it builds a block the user pastes back, its first
line `grill-me: <target>, round <n>`, then each `Qn:` with the answer indented
two spaces under it. An answer equal to its recommendation accepts it, an
empty one leaves the question open, and a block that matches no round is said
to match none.
