# Runner

Use the test command the repo declares (a `test` target, `package.json`'s `scripts.test`, the runner its manifest configures), and put new tests beside the existing ones, named alike. With none, initialise the language's standard runner with a module test per core module and `tests/scenarios/`, the end-to-end runs, tagged `@load` and `@fault`; fold old unit tests into the module test they exercise.

Set `VERIFY_TESTS` to that command in the repo's `.claude/settings.json` `env`, for `${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/verify.sh`, which a hook runs before each `git commit` and before a stop with changes; its passing at the repo's root is done.
