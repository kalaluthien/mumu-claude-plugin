# Write

Turn a task into one plan JSON the owner can answer in a minute.

## Steps

1. Put the goal first as a Part with `"kind": "goal"`.
2. Write what is settled as Parts: steps, evidence, notes. One sentence each, children under the Part they explain.
3. Write each open choice as a Decision. Make `pick` your own best option, and put the others in `else`.
4. Under each Option put its consequences in `parts`. Give a consequence `"kind": "risk"` when it can hurt. Give an Option that changes a screen a `"kind": "mockup"` Part: the screen as fixed-width text, one line per row, `[[x]]` for its main button and `[x]` for another.
5. Put the reason for an Option in a `"kind": "note"` Part under it, with its `source`; the page shows it in full, so the owner judges the pick without asking.
6. Give an Option a follow-up (`then`) only when the choice changes what to ask next. Never nest a second follow-up.
7. Put a `source` on a Part that rests on evidence: a url, a file and line, or a name.
8. Save as `<name>.json` and run `check-plan.py <name>.json`. Fix each refusal by its rule id in [grammar.md](grammar.md).

## Rules

- Ask only what changes the work; a Decision whose options lead to the same work is a note.
- The default must be the option you would take without an answer, because a kept Part costs the owner nothing.
- Read [../examples/implementation-plan.json](../examples/implementation-plan.json) for a plan with steps, risks and open questions, [../examples/incident-queue.json](../examples/incident-queue.json) for Decisions with follow-ups, and [../examples/visual-strategies.json](../examples/visual-strategies.json) for mockups.
