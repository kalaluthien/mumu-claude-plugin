---
name: spec
description: Use when a change touches states, transitions, a lifecycle, permissions, ownership or a protocol, or a rule stated as never, always, only after or at most - even if only the code was asked for - or when `*.als` files model the changed code, or when asked what the specs cover. Not for one function's input and output, nor for a value - a threshold, a colour, a size, a photometric target (test).
user-invocable: false
---

# Spec

Model the change in Alloy, check the rule it must keep before the code changes, and keep the model one drawable map of the system.

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/lib/contract.md`; read it first.

## Find what the repo has

| found, in this order | do |
| --- | --- |
| a model in another checked language (TLA+, Quint, Lean) | use it and the checker the repo runs it with |
| no `alloy` on PATH | say so, name where to get it (alloytools.org), and stop before writing anything; never check a model by reading it |
| `*.als` files | keep their layout; read the model covering the change |
| none | initialise `spec/map.als`, and `spec/<module>/model.als` and `check.als` per module the change touches |

## Write the model

`spec/map.als` is the structure a person reads: `sig Module { calls: set Module }`, `sig Remote in Module`, and one lifecycle `trans` per module. A change inside one module leaves it alone. Asked for a picture, draw a Mermaid view from `calls` and `trans`; check none in.

```alloy
module model                       -- model.als: what the system is; no commands
sig Order { ... }                  -- a sig is the owner's noun
fact Wellformed { ... }            -- what the system guarantees by construction
pred refund[...] { ... }           -- a pred is a verb: one operation, its guard and its effect
```

```alloy
open model                         -- check.als: what must hold of it
-- "An order must never end up both shipped and fully refunded."
assert NeverShippedAndRefunded { ... }  -- named for what holds
check NeverShippedAndRefunded for 3 expect 0
run refund for 3 expect 1          -- shows the model has an instance
```

Properties come from the owner's words: each sentence stating never, always, only after or at most becomes one assert quoting it, ranked by harm (money, data, safety first). Each module asserts every step stays inside its `trans`, and each call into a `Remote` gets a `Fail` outcome with a check that the caller stays inside `trans`. Delete a field or edge that no rule reads.

A value is not modelled: `Int` wraps at the scope's width (-8..7 by default) and has no reals. Model its order or a small integer with `but N Int`; the value itself goes to `test`.

Syntax that misleads: a `module` name has no hyphen and equals its path; a temporal word (`before`, `after`, `once`) cannot name a pred. `always A implies B` is `(always A) implies B`; `P until Q` demands that `Q` comes, `Q releases P` does not.

## Check

Every `check` and `run` carries `expect`: `alloy exec` exits 0 on a counterexample without one. Run `${CLAUDE_PLUGIN_ROOT}/skills/spec/scripts/verify.sh` at the repo's root, never a copy in the repo: it names each missed or missing expect, and each `check` with no `refuses_<Name>` in a test file, one under `test/`, `tests/`, `__tests__/` or `androidTest/` or named `test_*`, `*_test.*`, `*.test.*` or `*Test.<ext>`, never under `spec/`, `docs/` or `build/`. Start at `for 3` and raise the scope while each check finishes within a minute.

## Check the code against the model

Each `pred`'s guard is a precondition the code checks before the effect, and its effect the only state it changes; each `fact` and `assert` is an invariant the code never breaks. Each `check <Name>` has a test `refuses_<Name>` that drives the entry point toward the forbidden state and fails when the guarding code is removed.

A green check can hold without its rule:

- An UNSAT alone names nothing, since the scope refuses too: pair it with a SAT at the same scope differing in one conjunct.
- `x.f in S` holds over an empty `x.f`: write `some x.f and x.f in S`. A `var` term outside a temporal operator is read at state 0: put it inside the `eventually` where the rule bites.
- A rule written into the event's own pred cannot redden: give it its own pred with a Defect run (expect 1), RepairExcludes (0) and RepairAdmits (1, the code's own sequence).
- A frame condition alone pins nothing: add a command from the empty state with the producer forbidden, expecting 0.
- Scope 1 of a sig makes two navigations one relation: run at 2 as well. A model wider than the code that reads it is a false claim.
