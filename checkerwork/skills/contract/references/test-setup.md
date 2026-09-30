# Test: setup

A repo with no test layout.

1. Look for the test command and folder the repo declares; with none, initialise the language's standard runner: [test/runner-playbook.md](test/runner-playbook.md).
2. Set `VERIFY_TESTS` in the repo's `.claude/settings.json` `env`, and run `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh` at the root; it passes.
3. Tell the owner "no test layout found; initialised <path>".
