# Check

Every `check` and `run` carries `expect`: `alloy exec` exits 0 on a counterexample without one. Run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` at the repo's root, never a copy in the repo: it names each missed or missing expect, each `check` with no `refuses_<Name>` and each flow run with no `scenario_<pred>` in a test file, one under `test/`, `tests/`, `__tests__/` or `androidTest/` or named `test_*`, `*_test.*`, `*.test.*` or `*Test.<ext>`, never under `spec/`, `docs/` or `build/`. Start at `for 3` and raise the scope while each check finishes within a minute.

A green check can hold without its rule:

- An UNSAT alone names nothing, since the scope refuses too: pair it with a SAT at the same scope differing in one conjunct.
- `x.f in S` holds over an empty `x.f`: write `some x.f and x.f in S`. A `var` term outside a temporal operator is read at state 0: put it inside the `eventually` where the rule bites.
- A rule written into the event's own pred, or an assert restating a `fact`, cannot redden: give it its own pred with a Defect run (expect 1), RepairExcludes (0) and RepairAdmits (1, the code's own sequence).
- A frame condition alone pins nothing: add a command from the empty state with the producer forbidden, expecting 0.
- Scope 1 of a sig makes two navigations one relation: run at 2 as well. A model wider than the code that reads it is a false claim.
