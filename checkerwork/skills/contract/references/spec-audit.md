# Spec: audit

Check the code against the model, observing it through the tests and the event log, and cut what no code or test uses.

1. Each `pred`'s guard is a precondition the code checks before the effect, and its effect the only state it changes; each `fact` and `assert` is an invariant the code never breaks. Read each against the code it names.
2. Each `check <Name>` has its `refuses_<Name>` test, and each module, a folder under `spec/` with a check, has at least one flow run, a run naming a pred alone (`run refund`, one use case the model allows), or else a `gap #<issue>` mark; each flow run has its `scenario_<pred>` test. A run with its own `{ }` body is a guard run, the SAT pairing a check, and needs none: [test/witness-playbook.md](test/witness-playbook.md).
3. A transition no test reads from state is observed by the event log: set `$SPEC_EVENTS`, run the scenarios, and check each logged step is in its module's `trans`; code with no line there is a gap to report.
4. Run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh`, which names each missing witness and missed expect ([spec/check-playbook.md](spec/check-playbook.md)), and report each gap.
5. Cut each `pred`, `fact` or `check` that no code or test uses, and run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` again; report each one cut.
