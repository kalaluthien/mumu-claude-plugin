---
name: spec
description: Use when a change touches states, transitions, a lifecycle, permissions, ownership or a protocol, or a rule stated as never, always, only after or at most - even if only the code was asked for - or when `*.als` files model the changed code, or when asked what the specs cover. Not for one function's input and output, nor for a value - a threshold, a colour, a size, a photometric target (test).
user-invocable: false
---

# Spec

Model the change in Alloy and check the invariant it must keep before the code changes: sigs, facts and one `check` per invariant, no scenarios.

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/skills/test/references/contract.md`; read it first.

## Find what the repo has

| found, in this order | do |
| --- | --- |
| a model in another checked language (TLA+, Quint, Lean) | use it and the checker the repo runs it with |
| no `alloy` on PATH | say so, name where to get it (alloytools.org), and stop before writing anything; never check a model by reading it |
| `*.als` files | use their layout; read the model covering the change |
| none | initialise `spec/<module>/model.als` and `spec/<module>/check.als` |

## Write the model

```alloy
module model                       -- model.als: what the system is; no commands
sig Thing { ... }
fact Wellformed { ... }            -- what the system guarantees by construction
pred step[...] { ... }             -- one operation
```

```alloy
open model                         -- check.als: what must hold of it
assert KeepsInvariant { ... }      -- what the change must not break
check KeepsInvariant for 3         -- named for what holds
run step for 3                     -- shows the model has an instance
```

A value is not modelled: `Int` wraps at the scope's width (-8..7 by default) and has no reals. Model its order or a small integer with `but N Int`; the value itself goes to `test`.

Syntax that misleads: a `module` name has no hyphen and equals its path; a temporal word (`before`, `after`, `once`) cannot name a pred. `always A implies B` is `(always A) implies B`; `P until Q` demands that `Q` comes, `Q releases P` does not.

## Check

```sh
out=$(mktemp -d)/alloy
alloy exec -f -q -o "$out" spec/<module>/check.als && ls "$out"
```

| in `$out` | means |
| --- | --- |
| `<Check>-solution-0.md` | a counterexample, the file itself |
| no file for a `check` | it holds within its scope |
| `<Run>-solution-0.md` | the `run` found an instance; none means the facts contradict |
| nothing, and a non-zero exit | the model did not parse; read the error |

`exec` runs only the root file's commands (`-c <name>` picks one); `-o -` drops the result lines. Re-run after each edit to either file, editing none while a run continues. Start at `for 3` and raise the scope while each check finishes within a minute; report the scope each ran at.

## Check the code against the model

Each `pred`'s guard is a precondition the code checks before the effect, and its effect the only state it changes; each `fact` and `assert` is an invariant the code never breaks. For each, name the code that enforces it and the test that fails when that code is removed; one with neither is a gap: report it.

A green check can hold without its rule:

- An UNSAT alone names nothing, since the scope refuses too: pair it with a SAT at the same scope differing in one conjunct.
- `x.f in S` holds over an empty `x.f`: write `some x.f and x.f in S`. A `var` term outside a temporal operator is read at state 0: put it inside the `eventually` where the rule bites.
- A rule written into the event's own pred cannot redden: give it its own pred with a Defect run (expect 1), RepairExcludes (0) and RepairAdmits (1, the code's own sequence).
- A frame condition alone pins nothing: add a command from the empty state with the producer forbidden, expecting 0.
- Scope 1 of a sig makes two navigations one relation: run at 2 as well. A model wider than the code that reads it is a false claim.
- Mutate a rule before trusting it: break its guard once and its frame once, and watch each check go red.
