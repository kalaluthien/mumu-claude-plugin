# Write

Turn a task into one plan JSON the owner can answer in a minute.

## Steps

1. Put the goal first as a Part with `"kind": "goal"`.
2. Write what is settled as Parts: steps, evidence, notes. One sentence each, children under the Part they explain.
3. Write each open choice as a Decision. Make `pick` your own best option, and put the others in `else`.
4. Under each Option put its consequences in `parts`. Give a consequence `"kind": "risk"` when it can hurt. Give an Option that changes a screen a `"kind": "mockup"` Part: the screen as fixed-width text, one line per row, `[[x]]` for its main button and `[x]` for another.
5. Put the reason for an Option in a `"kind": "note"` Part under it, with its `source`; the page shows it in full, so the owner judges the pick without asking.
6. Write a question that only one answer raises as a later Decision with `requires`, and an option an earlier answer rules out with `excludes` or `requires`. Give a `name` only to what a relation names.
7. Put `files` on the plan and on an Option that adds work: your estimate of the files touched. Quote the owner or a source in a `"kind": "quote"` Part and show a change in a `"kind": "diff"` Part, plain text the page draws as it is.
8. Put a `source` on a Part that rests on evidence: a link a person can open, or `<person>, YYYY-MM-DD`; never a file path, an internal id, a tool or an agent name, and a claim with none is dropped or written as a `guess` (its text starts `Guess: `).
9. Save as `<name>.json` and run `check-plan.py <name>.json`. Fix each refusal by its rule id in [grammar.md](grammar.md).

## Rules

- **Ask less**: ask only what changes the work, as [decision-points.md](decision-points.md) says; a Decision whose options lead to the same work is a note.
- **On its Part**: put a Decision under the Part it changes, and at most 5 children under a Part, so the closed tree tells the plan.
- **Default**: the default must be the option you would take without an answer, because a kept Part costs the owner nothing.
- **Content language**: write the plan's content in the language of the request, since only the content speaks to the reader; in Korean, take a term's settled Sino-Korean word first, else its transliteration with the English beside it, such as `웹훅(webhook)`.
- **Examples**: read [../examples/implementation-plan.json](../examples/implementation-plan.json) for a plan with steps, risks and open questions, [../examples/incident-queue.json](../examples/incident-queue.json) for Decisions one answer raises, [../examples/scheduled-send.json](../examples/scheduled-send.json) for blocked options, estimates and exhibits, [../examples/visual-strategies.json](../examples/visual-strategies.json) for mockups, and [../examples/payment-webhook.json](../examples/payment-webhook.json) for Korean content.
