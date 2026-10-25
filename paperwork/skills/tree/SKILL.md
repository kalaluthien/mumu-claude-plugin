---
name: tree
description: Use when a plan or a set of decisions must go to the owner as a page they answer, and the answer must come back into the plan. Not for a one-off question or a diagram.
---

# tree

Write a plan as one JSON document, show it as one fixed HTML page, and read the owner's copied Answer back into the plan's next version. The shape of the grammar makes the wrong plans unwritable; the checker refuses the rest.

## Domain

- **Part**: one sentence in a tree, with an optional `kind`, `source` and child `parts`. Goal, step, evidence, risk, note, consequence and mockup are kinds of Part, not types.
- **Decision**: a Part that carries a `pick`, the agent's default Option, and optional `else` Options.
- **Option**: one choice with its consequences in `parts`; it may hold one follow-up Question, one level deep.
- **Answer**: the owner's reply as one Markdown line per Part touched; a Part with no line is kept.
- **id**: a Part's tree position, such as `1.2.1`, computed and never written.

The full grammar, with the checker's rule ids, is [references/grammar.md](references/grammar.md).

## Route

`Read` the playbook of the first row that fits the ask.

| ask | playbook |
| --- | --- |
| write a plan document from a task | [references/write.md](references/write.md) |
| show a plan to the owner, or read a pasted Answer back | [references/show.md](references/show.md) |

## Rules

- **Checked plan**: run `${CLAUDE_PLUGIN_ROOT}/skills/tree/scripts/check-plan.py <plan>` after every edit; a plan that does not print `ok 1` is not shown.
- **Scripts compute**: ids, pages and next plans come from `${CLAUDE_PLUGIN_ROOT}/skills/tree/scripts/make-page.py` and `${CLAUDE_PLUGIN_ROOT}/skills/tree/scripts/read-answer.py`, never from your own edits of the Answer.
- **One page**: every plan uses the same page; change the plan, never the page.
- **Examples**: [examples/](examples/) holds twelve finished plans, the report on this skill among them, each with the Answer a reader could paste back.
