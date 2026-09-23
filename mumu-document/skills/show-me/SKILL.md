---
name: show-me
description: Use when the answer is settled and must be shown - explain, draw, map, walk through or compare something as a document, a diagram or a page, or say only what the facts imply and what to do next (so what); not when the answer is still the user's to make (grill-me).
---

# show-me

Show the topic, the one named or else the conversation's, as a document:
load the `writing-documents` skill first and write it by that skill. A blank
is not shown: hand the document to `grill-me`.

Deliver it where the ask says, else where it is obvious, else ask once with
`AskUserQuestion`:

- chat: markdown;
- GitHub issue: the body or a comment by the repository's procedure, else
  `gh issue create`;
- page: `show-me-<slug>.html` in the session's scratch directory, published
  with the `Artifact` tool, else opened with `open`;
- repository page: where the repository keeps pages, linked from its README,
  landed by its procedure.

Delivered elsewhere, give the one-sentence version in chat.
