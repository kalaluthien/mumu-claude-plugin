---
name: show-me
description: Use when the answer is settled and must be shown - explain, draw, map, walk through or compare something as a document, a diagram or a page, or say only what the facts imply and what to do next (so what); not when the answer is still the user's to make (grill-me).
---

# show-me

Show the topic, the one named or else the conversation's, as a document of
`${CLAUDE_PLUGIN_ROOT}/doctype.md`; read it first. A blank is not shown: hand
the document to `grill-me`.

1. **Doctype**: the question picks it; build its parts in order.
2. **Medium**: markdown in one of its forms, or a page from
   `${CLAUDE_PLUGIN_ROOT}/page.html`.
3. **Plan**: one line naming the doctype, each figure with the paragraph
   beside it, and what the figure budget forces out; then write.
4. **Check** a page: `"${CLAUDE_PLUGIN_ROOT}/bin/page-check" <page>` prints
   `pass`; on `FAIL`, fix and rerun; exit 2 is a wrong path.
5. **Deliver** where the ask says, else where it is obvious, else ask once
   with `AskUserQuestion`:
   - chat: markdown;
   - GitHub issue: the body or a comment by the repository's procedure, else
     `gh issue create`;
   - page: `show-me-<slug>.html` in the session's scratch directory,
     published with the `Artifact` tool, else opened with `open`;
   - repository page: where the repository keeps pages, linked from its
     README, landed by its procedure.

   Then give the one-sentence version in chat.
