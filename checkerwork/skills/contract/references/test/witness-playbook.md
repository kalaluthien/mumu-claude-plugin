# Witnesses

The tests `spec/` requires, which `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` looks for by name:

- Each `check <Name>` has a `refuses_<Name>` test that drives the entry point toward the forbidden state and fails on the rule's own assertion when the guarding code is removed, at the lowest level that reaches the rule: a module test, else an end-to-end run on the real platform (a device, a browser, a live service), else the event log. A test that dies before its assertion (a missing dispatcher, a platform class, an image never decoded) reaches nothing: move it up a level, never land it as a gap.
- Each use case in the owner's words, a user doing one thing to its end, is a flow `run <pred>` with a `scenario_<pred>` test that drives it end to end.
- Where `$SPEC_EVENTS` is set, tests assert that each step it logs is in the module's `trans`.
- A `@load` scenario runs at twice the largest limit the code declares, with zero errors and no step outside `trans`; a `@fault` scenario fails each `Remote` call once.
