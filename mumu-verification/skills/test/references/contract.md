# Contract

A change is checked against a contract that predates it, stated so that a check can fail.

| term | meaning |
| --- | --- |
| contract | what a change must keep: a relation over a whole class of inputs, including what must not happen |
| path | the route an effect takes through the modules: the boundaries it crosses, in order, and where it stops |
| failure mode | a way the system was seen failing in a trace, named for this product |
| layout | where a repo keeps its specs, tests or evals, and the command that runs them |
| bar | which checks a change must pass; the project's to set |

## Rules

- Use the repo's layout. With none, initialise the default the skill names and tell the owner "no <kind> layout found; initialised <path>".
- Read the bar where the repo states it (CI, a contributing guide, agent instructions); with none, every check the change touches passes, and a skill's number is its default. Asked where verification stands, give each kind's layout, coverage, last result and gap to the bar.
- The owner sets the bar and judges traces; the agent writes the checks and the change, and never judges a trace for the owner.
- Write the check before the change and watch it fail for the reason the change addresses. An eval comes first only for a failure mode seen in a trace or a hard constraint the owner stated; otherwise error analysis does.
- A before and after is a delta only from the same instrument, run, unit and sha: re-measure the old side, and restart after a merge mid-run rather than splice.
- A check asserts a contract or a path, never one output byte for byte.
- A failing check is a defect in the change or the design: never loosen a check, a fact or a scope to make it pass.
- The project's process is its own: these rules hold inside any order of work.

## Breaking a check

A check is evidence only once a break of its subject turns it red: break it once, watch it fail, restore. It stays green anyway when something else answers, or when the break never landed.

Something else answers:

- A state the code must set (cwd, an env var, an installed tool, the clock): put the case in the opposite state first.
- A stub returns only the fields asked for, and a shim arm matches exactly (`issue view 5` also matches `issue view 500`). A suite that shells out shims every network CLI, refusing by default.
- Drive the case through the entry point, never arguments passed by hand.
- Assert text only the branch under test prints: never one the input holds, sibling branches share, or the runtime could print.
- Pair an absence with a presence, since it passes when the subject never ran; test a new refusal where every other path allows.
- Assert at a seam the subject owns, and cite the line that shows a fixture's claimed shape.

The break never landed:

- Assert each mutation applied (the old text found once, one per call site) and read the file back.
- Score a mutant only on a named failing case against an unmutated run: a crash without one is a harness death.
- Before reporting "uncovered", run the mutant by hand and watch the output differ; fix the fixture, never the mutation. Run it against every suite.

List mutants from the code, never from your own cases: each statement's effect alone; each regex anchor and quantifier; each half of a union and each conjunct, with its near-miss case; a gate to true and to false; a helper to a constant; a table cut to one row. After loosening a comparison, run every mutant again: a new survivor is an invariant the strict form held by accident. Asked whether a behaviour exists, answer with a mutation, not a read.
