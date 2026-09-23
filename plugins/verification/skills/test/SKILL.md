---
name: test
description: Use when a behaviour is added, changed or fixed - a feature, a bug fix, an endpoint, a command - writes the failing acceptance and integration tests first, then the change that makes them pass; not for a refactor that keeps behaviour, which the existing tests already cover.
---

# Test

A test asserts a functional contract, not an implementation's output byte for byte.

| kind | exercises |
| --- | --- |
| acceptance | the app as a user drives it: the CLI, the HTTP API, the UI |
| integration | one module against real infrastructure: the database, the filesystem, the network |

## 1. Find what the repo has

Look for a declared runner, in this order, and use the first found:

| file | runner |
| --- | --- |
| `justfile` / `Makefile` with a `test` target | `just test` / `make test` |
| `package.json` `scripts.test` | `npm test` |
| `pyproject.toml` with `[tool.pytest]` or a `pytest` dependency | `pytest` |
| `Cargo.toml` | `cargo test` |
| `go.mod` | `go test ./...` |

Put new tests where the repo's existing tests live and name them the way they are named.

If none is found, initialise `tests/acceptance/` and `tests/integration/` with the language's standard runner (pytest, vitest, `cargo test`, `go test`), and tell the owner "no test layout found; initialised `tests/acceptance/` and `tests/integration/` with <runner>".

## 2. Red

Write one acceptance test and one integration test for the behaviour. Run them and read the failure: it must fail for the missing behaviour, not for an import error or a typo.

## 3. Green

Make the change. Run the new tests and the whole suite; both pass.

## 4. Prove the test can fail

Undo the change alone, watch the new tests fail, and restore it. A test that passes without the change is not evidence.
