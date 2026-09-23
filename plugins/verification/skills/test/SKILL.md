---
name: test
description: Use when a behaviour is added, changed or fixed - a feature, a bug fix, an endpoint, a command - writes the failing acceptance and integration tests first, then the change that makes them pass; not for a refactor that keeps behaviour, which the existing tests already cover.
---

# Test

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/contract.md`; read it first.

## 1. Find what the repo has

Use the test command the repo declares: a `test` target, `package.json`'s `scripts.test`, or its language's runner configured in its manifest. Put new tests where the existing ones live, named the way they are.

If none is found, initialise `tests/acceptance/` and `tests/integration/` with the language's standard runner (pytest, vitest, cargo, go).

## 2. Red

Write one acceptance test and one integration test for the behaviour. Run them and read the failure: it must fail for the missing behaviour, not for an import error or a typo.

## 3. Green

Make the change. Run the new tests and the whole suite; both pass.

## 4. Prove the test can fail

Undo the change alone, watch the new tests fail, and restore it.
