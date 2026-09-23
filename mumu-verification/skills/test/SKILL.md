---
name: test
description: Use when a change alters what code does - a bug fix, a feature, a new rule, an endpoint, a command - even if only the fix was asked for or the repo has no tests, or when asked what the tests cover. Not for a refactor that keeps behaviour.
---

# Test

Write the failing acceptance and integration tests first, then the change that makes them pass.

Terms and rules: [contract](references/contract.md); read it first.

## 1. Find what the repo has

Use the test command the repo declares: a `test` target, `package.json`'s `scripts.test`, or its language's runner configured in its manifest. Put new tests where the existing ones live, named the way they are.

If none is found, initialise `tests/acceptance/` and `tests/integration/` with the language's standard runner (pytest, vitest, cargo, go).

## 2. Red

Write one acceptance test and one integration test for the behaviour, each asserting a contract or a path:

| a bare equality | a contract or a path |
| --- | --- |
| `add("")` returns `None` | every blank title (empty, spaces, a tab) exits non-zero with a message, and the stored list is unchanged |
| the refund call returns 200 | a refund reaches the payment gateway once, before the order reads refunded, and never for an unpaid order |

A screen is checked by driving it in a browser and asserting what it shows. Run the tests.

## 3. Green

Make the change. Run the new tests and the whole suite; both pass. Then undo the change alone, watch the new tests fail, and restore it.
