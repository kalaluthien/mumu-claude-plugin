# Model

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
run refund for 3 expect 1          -- a flow run: the use case has an instance
```

Properties come from the owner's words: each sentence stating never, always, only after or at most becomes one assert quoting it, ranked by harm (money, data, safety first). Each module asserts every step stays inside its `trans`, and each call into a `Remote` gets a `Fail` outcome with a check that the caller stays inside `trans`; these two quote the `trans` or the `Remote` they guard, not an owner's sentence. State that changes hangs on the noun it belongs to as a `var` field, never on one `Time` sig holding every field, so a drawn sig shows its own state. Delete a field or edge that no rule reads.

A value is not modelled: `Int` wraps at the scope's width (-8..7 by default) and has no reals. Model its order or a small integer with `but N Int`; the value itself goes to a test ([contracts-playbook.md](../test/contracts-playbook.md)).

Syntax that misleads: a `module` name has no hyphen and equals its path; a temporal word (`before`, `after`, `once`) cannot name a pred, nor a command keyword (`check`, `run`, `expect`, `for`, `but`) a sig, field or pred: it is a syntax error at its first use. `always A implies B` is `(always A) implies B`; `P until Q` demands that `Q` comes, `Q releases P` does not.
