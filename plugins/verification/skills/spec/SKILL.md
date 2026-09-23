---
name: spec
description: Models a change in Alloy and checks the invariant it must keep before the code changes. Use for any change to states, transitions, a lifecycle, permissions, ownership or a protocol, or to a rule stated as never, always, only after or at most - even when the request asks only for the code - and when `*.als` files model the changed code, or asked what the specs cover; not for one function's input and output, which a test states.
---

# Spec

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/contract.md`; read it first.

## 1. Find what the repo has

```sh
command -v alloy
git ls-files '*.als'
```

| found, in this order | do |
| --- | --- |
| no `alloy` on PATH | say so and stop before writing anything; never check a model by reading it |
| `*.als` files | use their layout; read the model covering the change |
| none | initialise `spec/<module>/system.als` |

## 2. Write or edit the model

```alloy
module <module>/system

sig Thing { ... }

fact Wellformed { ... }            -- what the system guarantees by construction

pred step[...] { ... }             -- one operation

assert KeepsInvariant { ... }      -- what the change must not break
check KeepsInvariant for 3
```

- One `check` per invariant; name it for what holds.
- A fact states what the design enforces, never what the check needs to pass.

## 3. Check

```sh
out=$(mktemp -d)/alloy
alloy exec -f -q -o "$out" spec/<module>/system.als && ls "$out"
```

| in `$out` | the `check` |
| --- | --- |
| `<Check>-solution-0.md` | found a counterexample; the file is it |
| no file for it | holds within its scope |
| nothing, and a non-zero exit | the model did not parse; read the error |

- Re-run every `check` in the file after each edit.
- Start at `for 3` and raise the scope while each check finishes within a minute; report the scope each ran at.

## 4. Check the code against the model

Each `pred` is an operation: its guard is a precondition the code checks before the effect, and its effect the only state it changes. Each `fact` and `assert` is an invariant the code never breaks. For each, name the code that enforces it and the test that fails when that code is removed; one with neither is a gap: report it.
