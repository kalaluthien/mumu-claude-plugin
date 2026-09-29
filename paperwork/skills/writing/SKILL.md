---
name: writing
description: Use before writing markdown a person reads outside the chat - a GitHub issue or pull request body or comment, a README or another repository markdown page - to explain, report, propose or walk through something in text. Not for an Artifact or HTML page, such as a proposal, a specification or teaching material built as a page (that is `rendering`), nor for a plain chat answer, nor for code or its comments, nor for asking the user open questions (that is `grill-me`).
user-invocable: false
---

# writing

**Goal**: the reader gets what they need, in the order they need it, and can act on it. A format the running skill or the repository states wins: its template, headings, comment kinds. Delivered anywhere, give the one-sentence version in chat.

## Shape

The reader's situation picks the moves, in order; a move with nothing to say is dropped.

| the reader | moves, in order |
| --- | --- |
| must agree to what is not settled: an issue, a plan, a choice | the goal and when it is done · why, and the options against criteria fixed first · the recommendation and the fact that would change it |
| must understand or use what is settled: a README, a doc, a pull request | what it is and how it works · the steps, each with its check · what was done, its proof, the next action |

1. **Answer**: the reader's question and the answer in one sentence, before the first heading; it claims no more than the proof below shows.
2. **Headings**: the moves, each a noun phrase carrying its section's claim (the rename that breaks scripts, not Changes); siblings neither overlap nor leave a gap; the headings read alone state the argument.
3. **Order**: overview to detail, each section answering the question the one before raises; time order only for a sequence.
4. **Ending**: what the reader does next, or that nothing is needed; no summary.

## Text forms

Each section takes the one form that carries its point: a sentence for a claim, a list for parallel items, a table only for values compared across rows, narrow, its first column the row's label. Prefer explaining through one good example where one exists: a short code block, a command and its output, or a before/after.

| when the content is | in markdown |
| --- | --- |
| files and modules, their roles | a code-block tree, one comment per line |
| a structure before and after a change | a diff of the tree |
| what happens in one use case | a numbered list of calls |
| things and the links between them | a list: each node, then the nodes it links to |
| values compared, or a change over time | a table |
| a result that follows inputs | the formula, then a table of a few inputs and results |
| where a fact comes from | a line `출처: [title](url), date → [title](url)` |

No Mermaid, HTML or image by default. A structure or behaviour text cannot carry is drawn as a `rendering` widget on a page and written as SVG by its `check.py <page> --svg <dir>`; on GitHub reference it as `![<alt>](./<page>-<n>.svg)` and pass `--attach './<page>-<n>.svg#<alt>'` to `gh`, again on every later edit of the body; on a repository page, commit it beside the page.

## GitHub and repository pages

- An issue, pull request or comment follows the repository's procedure, else `gh issue create`; a repository page is linked from the README and lands by a pull request.
- Unless the procedure sets the form, a pull request body is one sentence on why the change exists, the proof (each check run and its result), then the files in reading order, each with its why; a misleading line count is called out.
- A `path:line` links to the blob at the head sha, or relatively on a repository page; code is quoted as a sha permalink with a line range on its own line, not pasted.

## Sentences

- Name things instead of counting them: a count goes stale, a name can be grepped.
- Short words, one idea a sentence, active voice; a new term is defined where it first appears or cut; no word that sells. A change you judge wrong is said so, plainly; a reason the source omits is called absent, not guessed.
- Korean text takes the formal -습니다/-ㅂ니다 endings, never -요 or a plain -다.
- A measurable quantity carries its unit, beside the number or in the table header, as 지연(ms).

## Done when

- A part no fact settles goes to `grill-me` by name; the text carries only its settled answers.
- Reread: the headings read alone state the argument, each section's first sentence is its point, each claim has its proof, and nothing is left that does not serve the reader's next action; fix each miss.
