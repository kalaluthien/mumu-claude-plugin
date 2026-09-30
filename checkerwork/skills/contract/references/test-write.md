# Test: write

A change to what code does: write the failing tests first, then the change that makes them pass.

1. A repo with no test layout, only then: use the test command and folder it declares, else initialise the language's standard runner ([test/runner-playbook.md](test/runner-playbook.md)); set `VERIFY_TESTS` in `.claude/settings.json` `env`; run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` at the root, and it passes; tell the owner "no test layout found; initialised <path>".
2. Find the repo's test command and where its tests sit: [test/runner-playbook.md](test/runner-playbook.md).
3. Red: write an acceptance test and an integration test, each asserting a contract or a path ([test/contracts-playbook.md](test/contracts-playbook.md)). A change the model in `spec/` covers also gets its witnesses ([test/witness-playbook.md](test/witness-playbook.md)). Run the tests and watch each fail for the reason the change addresses.
4. A plugin change `claude plugin eval` cannot reach (a hook, a dialog, a monitor, the `/` menu, a skill's trigger in a real session) is checked in live sessions instead, the default branch beside the change: run both sides and read each ([test/probe-playbook.md](test/probe-playbook.md)); replay a trigger change beside the plugins a session really loads with `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/replay.py` ([eval/graders-playbook.md](eval/graders-playbook.md)); report each side's result, main beside branch, quoting the pane or transcript lines that show it.
5. Green: make the change. Run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh`; it passes. Then undo the change alone, watch the new tests fail, and restore it.
