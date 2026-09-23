---
name: show-me
description: Use when the answer is settled and must be shown - explain, draw, map, walk through or compare something as a document, a diagram or a page; not when the answer is still the user's to make (grill-me).
---

# show-me

Show the topic instead of describing it: the one named, else whatever the
conversation is about. Every rule for the document is in
[doctype](doctype.md); read it before writing.

An open choice is not shown: hand it to `grill-me`.

## The steps

1. **Doctype**: the question the ask puts picks a `diagram`, a `narrative`
   or a `comparison` (doctype § Doctypes); build its parts in that order.
2. **Medium**: doctype § Media. Markdown takes the chat forms below; a page
   starts from [page.html](page.html).
3. **Plan**: say in one line the doctype, each figure and the paragraph
   beside it, and what the figure budget (doctype § Figures) forces out;
   then write.
4. **Check**: a page passes doctype § Check before it is delivered.
5. **Ending**: doctype § Delivery.

## The chat forms

Pick the smallest form that makes the point, put it next to the short text it
supports, and keep only the calls, files, states and boundaries the question
needs.

| form | for |
| --- | --- |
| pseudocode | logic or an algorithm |
| a call tree | runtime control flow |
| a component tree, with the state and module boundaries that matter | UI structure |
| a shallow file tree, one comment per line | file responsibility, a broad refactor |
| a table, a row per option, bold only on the cells the verdict turns on, a line under it saying so | a comparison |
| a diff in the shape of one of the above | what changes in a shape that already exists |
| the whole block | most of it is new, or omitted context would hide order or ownership |

```text
submitForm
  createSession
    persistPrompt
    launchAgent
  navigateToSession
```
