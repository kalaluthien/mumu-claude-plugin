# Alloy

## Running (§ 3)

- `exec` runs only the root file's commands, never an opened module's; `-c <name>` runs one, and takes a wildcard or an index.
- `-o -` streams solutions and drops the result lines: send output to a directory.
- A `module` name has no hyphen and equals its path from where `open` resolves; a temporal word (`before`, `after`, `once`, `always`) cannot name a fun or pred.
- `always A implies B` parses as `(always A) implies B`: write `always (A implies B)`. `and` binds tighter than `or`, `implies` and `iff`; `P until Q` demands that `Q` comes, `Q releases P` does not.
- `Int` wraps without `-n`: read a counterexample's integers for a sign flip, and guard an addition the way the code does.
- `for ..., m..n steps` sets a floor that speeds a long run; never on a check expected to hold. A `var` field of arity 4 or more on a `one sig` stalls: make the tuple a sig.
- Edit no file while a run on it continues.

## A check green without its rule (§ 4)

- An UNSAT alone names nothing, since the scope refuses too: pair it with a SAT at the same scope differing in one conjunct. After relaxing a constraint, require that pair to go UNSAT to SAT, or the re-check never visited the new states.
- `x.f in S` holds over an empty `x.f`, and `all` over a `var` set holds once an event empties it: write `some x.f and x.f in S` with a `no x.f` control, and pin the set's size.
- A `var` term outside a temporal operator is read at state 0, a quantifier's domain too: put it inside the `eventually` where the rule bites. Two bare `eventually`s carry no order: write `eventually (X and after always not X)`.
- A witness satisfies itself another way: naming only the end state, by changing the premise first; naming only the pre-state, without the update (add `after <post-state>`); through another disjunct (negate the others); through the constraint's escape hatch (exclude it).
- A rule written into the event's own pred, or an assert built from its guard, cannot redden: give the rule its own pred with Defect (expect 1), RepairExcludes (expect 0) and RepairAdmits (expect 1, the code's own sequence).
- A frame condition alone pins nothing: add a command from the empty state with the producer forbidden, expect 0; for events defined only by their effect, make the actor a `var` singleton each event sets.
- Scope 1 of a sig makes two navigations one relation: run the command at 2 as well. A witness calling the rule's own helper moves with a mutant of it: spell the navigation out.
- Fairness is weak: `always (enabled implies eventually fires)`; an antecedent true where nothing is enabled makes liveness UNSAT with no trace.
- Deleting a field drops the bound a fact put on it: rewrite each read as the bound plus the remainder. A model wider than the code that reads it is a false claim.
- Mutate a rule before trusting it: break its guard once and its frame once, and watch each check go red.
