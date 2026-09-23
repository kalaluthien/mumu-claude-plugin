---
name: grill-me
description: Use when the answer is still the user's to make - a decision, a proposal, a plan or an issue body with open choices to settle by asking them; not when the facts settle it (show-me) or code is under review.
---

# grill-me

The document to produce decides the questions: each blank in it is one. A
target the ask does not name is a proposal.

## The targets

| target | its blanks | the result |
| --- | --- | --- |
| an issue or a template the repository keeps | that template, found through the repository's `AGENTS.md` or `CLAUDE.md` and read now, never copied | its markdown body |
| a proposal: one idea weighed against leaving things as they are | the question; the yardstick, fixed before any option; each option against it; the verdict and what would change it | markdown |
| a decision | a numbered veto table: `#`, ruling, reason, one line each | markdown |

The repository's template or rule decides the rest -- a title, a first line,
a ceiling -- and is read at run time, never restated here.

## The rounds

- Map the blanks as a tree: a blank waits while one it rests on is open, as a
  definition of done waits on its scope.
- The **frontier** is every blank whose prerequisites are settled. Each round
  asks the whole frontier and nothing below an open blank. Number each
  question `Q1`, `Q2`, with `Recommended:` and your answer under it. Then
  wait.
- Facts are yours to find: look them up, by a subagent when it takes a
  search. Put only decisions to the user. A pending lookup holds back only
  the blanks under it.
- Attack each answer once before writing it: a counterexample, an edge case,
  a check that can fail, a term the repository uses otherwise, or code that
  says otherwise. Write it once it survives, or once the user restates it
  knowing the attack.
- Done when every blank is filled and the user confirms the document. Act on
  nothing before that.

## Where a round is asked

| the round | where |
| --- | --- |
| four questions or fewer, with `AskUserQuestion` in the session | `AskUserQuestion` |
| more, with the `Artifact` tool in the session | [form.html](form.html), one fieldset per question, its recommendation prefilled, published with that tool |
| otherwise | numbered text in chat |

The form writes nowhere. It builds one block the user pastes back; its first
line is `grill-me: <target>, round <n>`. Read it against that round, or say it
matches no round. Under each `Qn:` line, indented two spaces, is that answer
verbatim: one equal to its recommendation accepts it, an empty one leaves the
question open. Click its button once before publishing.

## The ending

The confirmed document goes where the ask says, else ask once with
`AskUserQuestion`: chat, a GitHub issue, or a page. A page is `show-me`'s:
invoke it with the document.
