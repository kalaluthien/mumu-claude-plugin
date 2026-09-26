---
name: test
description: Use when a change alters what code does - a bug fix, a feature, a new rule, an endpoint, a command - even if only the fix was asked for or the repo has no tests, or when asked what the tests cover. Not for a refactor that keeps behaviour.
user-invocable: false
---

# Test

Write the failing acceptance and integration tests first, then the change that makes them pass.

Terms and rules: [contract](references/contract.md); read it first.

## Find what the repo has

Use the test command the repo declares (a `test` target, `package.json`'s `scripts.test`, the runner its manifest configures), and put new tests beside the existing ones, named alike. With none, initialise `tests/acceptance/` and `tests/integration/` with the language's standard runner.

## Red

Write an acceptance test (the app driven as its user drives it: the CLI, the HTTP API, the screen) and an integration test (one module against its real infrastructure: the database, the filesystem, the network), each asserting a contract or a path:

| a bare equality | a contract or a path |
| --- | --- |
| `add("")` returns `None` | every blank title (empty, spaces, a tab) exits non-zero with a message, and the stored list is unchanged |
| the refund call returns 200 | a refund reaches the payment gateway once, before the order reads refunded, and never for an unpaid order |

Drive a screen in a browser and assert what it shows; a Claude plugin's hook, dialog, monitor or `/` menu, by the plugin probe below. Run the tests.

A value rule - a threshold, a colour, a size - lives once as a named constant where the code reads it, and its test states the literal: `isFlat(5.0f)`, never `isFlat(TOLERANCE)`.

## Green

Make the change. Run the new tests and the whole suite; both pass. Then undo the change alone, watch the new tests fail, and restore it.

## Plugin probe

What `claude plugin eval` cannot reach is shown in live herdr sessions, main beside branch:

1. Sides: main's plugin dir is `git -C <checkout> worktree add --detach <scratch>/main origin/<default>`, the branch's its worktree; edit neither while its probe runs.
2. Start each side with the block below. The pane is `result.root_pane.pane_id`; names are lowercase; `agent_pane_busy` means the shell's rc still runs, so retry every 2 s. `--env` shortens a timer or puts a fake `gh` first on PATH. An untrusted cwd's folder dialog takes `herdr agent send-keys <pane> down`, then `enter`.
3. Drive with `herdr agent prompt <pane> "<text>"`, reading the pane and resending when a prompt right after start vanished. The `/` menu: `herdr pane send-text <pane> "/<plugin>:"` without enter, then `herdr pane read <pane>`: a hidden skill reads "No commands match", against a prefix that still lists one. A lead: cwd a scratch `git init` repo whose origin is `https://github.com/o/r.git`, so no GitHub write lands. A worker: the branch's `worker-start.py <checkout> probe-<x> low <issue-url>`, ended by `worker-close.py probe-<x>`.
4. Read `herdr agent read <pane> --lines 30`, a monitor by `ps`, and tool calls in the session's transcript ([eval](../eval/SKILL.md) § Transcripts).
5. End: `escape` a busy session, prompt `/exit`, close both tabs, remove main's copy, and report each side's result, main beside branch.

```sh
herdr tab create --cwd <trusted dir> --label probe-<side> --no-focus [--env KEY=VALUE]
herdr agent start probe-<side> --kind claude --pane <pane> -- --name probe-<side> --plugin-dir <dir> [--agent <plugin>:<agent>] --model opus --effort low
```
