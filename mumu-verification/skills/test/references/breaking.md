# Breaking a check

A check is evidence only once a break of its subject turns it red. It stays green anyway in two ways: something other than the subject answers, or the break never reached the behaviour.

## Something else answers

- A state the code must set (cwd, an env var, an installed tool, the clock): put the case into the opposite state first, since the runner may already hold it.
- A stub: name what it answers when the subject asks for the wrong thing. Return only the fields asked for, and match a shim arm exactly (`issue view 5` also matches `issue view 500`).
- Arguments passed by hand leave the call site unread: drive the case through the entry point.
- Assert text only the branch under test prints, never a string the input already holds (an echoed path), a word sibling branches share, or a message the shell or runtime could print.
- An absence, or a row of negatives, passes when the subject never ran: pair it with a presence. A new refusal is tested where every other path allows; a check keyed on a set, with a value the set never holds.
- A side effect of another script tests that script: assert at a seam the subject owns.
- A suite that shells out shims every network CLI, the shim refusing by default. A fixture's variables carry their own prefix: a subject reassigning an inherited variable keeps it exported, into the fake.
- A fixture that claims the real artifact's shape cites the line that shows it.

## The break never landed

- Assert a mutation applied (the old text found exactly once) and read the file back; label each by its site, one mutation per call site.
- Score a mutant only on a named failing case, against an unmutated run of the same copy: a crash with no named failure is a harness death, not a kill, and a case total the subject derives proves nothing.
- Before reporting "uncovered", run the mutant by hand on the case's input and watch the output differ: an edit can change nothing (a pattern that matched nothing, one half of a redundant pair, values the fixture holds equal), or still reach the old value. Fix the fixture, never the mutation.
- Run each mutation against every suite, since a sibling may pin it; then list ignored scratch paths, where a mutant that escaped containment writes.

## What to break

List mutants from the code, never from your own cases:

- each effect of a statement alone; each regex anchor, quantifier and lookbehind
- each half of a union, deleting a half whose mutation reddens nothing; each conjunct, with its near-miss case
- a gate to `True` and to `False`, with a case the branch must not claim
- a helper to a constant: nothing red means the wiring is untested
- a table-driven case: cut the table to one row and assert the column that varies
- a step whose exit status was the answer, once it gains a successor: `|| exit 1`, and a case where it refuses and later steps would admit
- after loosening a comparison, every mutant again: a new survivor is an invariant the strict form held by accident

Code declared dead is deleted only once no input reaches it; asked whether a behaviour exists, answer with a mutation, not a read.

## Shell fixtures

- `( cmd ) &` with one command is exec'd, so `$!` is `cmd`; a wrapper exists only as `( cmd; : ) &`.
- A stub for a SIGPIPE defect writes past the pipe buffer (64 KiB on macOS) and exits as its writer did.
- `pgrep -f` wait loops match each other: wait on an output file, or bracket the pattern (`'[x]-test.py'`).
