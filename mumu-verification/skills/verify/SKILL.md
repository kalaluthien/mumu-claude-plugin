---
name: verify
description: Use when a change in a repo holding a `spec/` model is to be called done, committed or reported - it runs the one gate over the Alloy model and the test suite. Not for writing the tests or the model (test, spec).
user-invocable: false
---

# Verify

Run `${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/verify.sh` at the repo's root, never a copy in the repo; exit 0 is done. It names each Alloy command that misses its `expect` or has none, each `check <Name>` with no `refuses_<Name>` in a test file, each `refuses_` naming no check, and a red suite.

- A test file sits under `test/`, `tests/`, `__tests__/` or `androidTest/`, or is named `test_*`, `*_test.*`, `*.test.*` or `*Test.<ext>`, never under `spec/`, `docs/` or `build/`.
- The suite is `$VERIFY_TESTS`: set it to the repo's test command in `.claude/settings.json`'s `env`.
- A hook runs the gate before each `git commit` and before a stop with changes, and refuses while it fails: fix the change or the model, never loosen an expect.
