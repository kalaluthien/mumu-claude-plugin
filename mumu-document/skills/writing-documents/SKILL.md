---
name: writing-documents
description: Use before writing any document, page or diagram a person will read - an explanation, a walkthrough, a comparison, a map, a report, an issue or pull request body, a page of questions - even when only the content was asked for. Not for code or its comments.
---

# writing-documents

Write the document by [doctype.md](references/doctype.md); read it first. A
format the running skill or the repository states wins over it: its template,
its headings, its comment kinds.

1. **Doctype**: the question picks it; build its parts in order. Asked only
   what follows, answer as `doctype.md` says, with no doctype.
2. **Medium**: markdown in one of its forms, or a page from
   [page.html](assets/page.html), whose `#round` form asks a round of
   questions.
3. **Plan** a page or a figure: one line naming the doctype, each figure
   with the paragraph beside it, and what the figure budget forces out; then
   write.
4. **Check** a page: `"${CLAUDE_PLUGIN_ROOT}/bin/page-check.sh" <page>` clicks
   each control once and prints `pass`; on `FAIL`, fix and rerun; exit 2 says
   why it could not run.
