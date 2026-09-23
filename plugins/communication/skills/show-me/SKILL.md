---
name: show-me
description: Use when the answer is settled and must be shown - explain, draw, map, walk through or compare something as a document, a diagram or a page; not when the answer is still the user's to make (grill-me).
---

# show-me

Show the topic instead of describing it: the one named, else whatever the
conversation is about. Every rule for the document is in
`${CLAUDE_PLUGIN_ROOT}/doctype.md`; read it before writing.

An open choice is not shown: hand it to `grill-me`.

## The steps

1. **Doctype**: the question the ask puts picks a `diagram`, a `narrative`
   or a `comparison` (doctype § Doctypes); build its parts in that order.
2. **Medium**: doctype § Media. Markdown takes doctype § Markdown forms; a
   page starts from `${CLAUDE_PLUGIN_ROOT}/page.html`.
3. **Plan**: say in one line the doctype, each figure and the paragraph
   beside it, and what the figure budget (doctype § Figures) forces out;
   then write.
4. **Check**: `"${CLAUDE_PLUGIN_ROOT}/bin/page-check" <page>` prints `pass`
   before a page is delivered; exit 2 means a wrong path.
5. **Ending**: § Delivery.

## Delivery

- Unless the ask says, ask once with `AskUserQuestion`: chat, a GitHub issue,
  a page, or a page kept in a repository. Do not ask when it is obvious.
- **Chat**: markdown, in doctype § Markdown forms.
- **GitHub issue**: the body or a comment, by the repository's own procedure,
  else `gh issue create`.
- **Page**: written to `show-me-<slug>.html` in the session's scratch
  directory, checked, then published with the `Artifact` tool when the
  session has it, else opened with `open`.
- **Repository page**: written where the repository keeps pages, checked
  there, linked from its README, landed by its own procedure.
- Whatever the ending, give the one-sentence version in chat.
