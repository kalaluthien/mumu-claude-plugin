# Size rubric

How `scripts/count-units.py` has Sonnet count mumu-team's text: every `.md`
file outside `tests/` and `evals/`, this one excepted, each line shown
numbered. Every item is cited by its file and line; an item spread over
several lines is cited at its first.

## Instruction

One independent directive that changes the reader's next action: what to do,
never to do, or the condition that decides which. A line, sentence or table row
carrying several directives counts each; a definition of a name is a term, not
an instruction, unless it also directs.

- Counts, as two: `Prefer dedicated file and search tools to the shell; run independent calls in parallel.`
- Does not count: `| topic | 2-4 lowercase words joined by hyphens |`, a definition that directs nothing.

## Duplicate

An instruction whose directive another instruction already states, in the same
file or another, whatever its wording. A group of n instructions stating one
directive counts n - 1 duplicates; every member is listed.

- Counts, as one: `A share's worker writes only its pull request and BLOCKED: <share>: ... comments on the task.`
  (lead-goal.md) beside `as a share's worker you write only your pull request and BLOCKED: <share>: ... comments`
  (work-task.md).
- Does not count: `start ... one Bash call of its own` beside `merge as a Bash call of its own`, the same form
  asked of two different commands.

## Elaboration

Text that changes no action: an explanation, a reason, an example, a
description of how something works. Each such sentence counts one, and so does
each reason or example clause inside a directive's sentence.

- Counts, as one: `since a remembered pane id can be stale`, the reason clause of `prompt ... by name`.
- Does not count: `by name` in the same sentence, the directive itself.

## Term

A proper name the reader must know to act: a word the text defines or uses as a
name (`share`, `claim`), a command, script or file (`worker-start.py`), a label
or keyword (`APPROVED:`). Each distinct name counts once across all files;
a word used in its everyday sense is none. A variant is a second name for an
entity another term already names, flagged with both names and where each is
used.

- Counts, as one: `worker-start.py`, however many files name it.
- Does not count: `folder` in `a Claude project folder`, an everyday word.
- A variant: `lead` beside `leader`, both naming the one session per project.
