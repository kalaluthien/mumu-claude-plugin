# Size rubric

How `scripts/size-count.py` has Sonnet count teamwork's text: every `.md`
file outside `tests/` and `evals/`, this one excepted, cut by code at each
sentence end and semicolon into sentences, each with an id and its line. Score
every sentence as [instructions, elaboration]; a sentence with neither, such as
a table row that only defines, scores [0, 0].

## Instruction

One independent directive that changes the reader's next action: what to do,
never to do, or the condition that decides which. A sentence or table row
carrying several directives scores each; a definition of a name directs
nothing unless it also says what to do. A rule the reader applies counts even
when stated as a fact: a criterion, a pass condition, an item of a checklist,
what a role the file addresses does (`You alone write APPROVED:`).

- Counts, as two: `Prefer dedicated file and search tools to the shell; run independent calls in parallel.`
- Does not count: `| topic | 2-4 lowercase words joined by hyphens |`, a definition.

## Duplicate

An instruction whose directive another instruction already states, in the same
file or another, whatever its wording. A group of n sentences stating one
directive counts n - 1 duplicates; list every member.

- Counts, as one: `A share's worker writes only its pull request and BLOCKED: <share>: ... comments on the task.`
  (lead-playbook.md) beside `as a share's worker you write only your pull request and BLOCKED: <share>: ... comments`
  (worker-playbook.md).
- Does not count: `start ... one Bash call of its own` beside `merge as a Bash call of its own`, the same form
  asked of two different commands.

## Elaboration

Text that changes no action: an explanation, a reason, an example, a
description of how something works. A sentence that directs nothing scores one;
a directive's sentence scores one for each reason or example clause it carries.

- Counts, as one: `since a remembered pane id can be stale`, the reason clause of `prompt ... by name`.
- Does not count: `by name` in the same sentence, the directive itself.

## Term

A proper name the reader must know to act, which the text either sets in code
format or defines: a word a table row or a sentence defines (`share`, `claim`),
a command, script, skill or file (`worker-start.py`), a label or keyword
(`APPROVED:`). Name a command by its program and subcommand, with no arguments
or flags; a heading, a placeholder such as `<url>` or a word in its everyday
sense is none. A variant is a second term for an entity another term already
names.

- Counts, as one: `worker-start.py`, however many files name it.
- Does not count: `folder` in `a Claude project folder`, an everyday word never defined.
- A variant: `kickoff` beside `/teamwork:kickoff`, both naming the one skill.
