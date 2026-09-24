---
name: spec
description: Use when a change touches states, transitions, a lifecycle, permissions, ownership or a protocol, or a rule stated as never, always, only after or at most - even if only the code was asked for - or when `*.als` files model the changed code, or when asked what the specs cover. Not for one function's input and output, nor for a value - a threshold, a colour, a size, a photometric target (test).
user-invocable: false
---

# Spec

Model the change in Alloy and check the invariant it must keep before the code changes.

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/skills/test/references/contract.md`; read it first.

## 1. Find what the repo has

```sh
command -v alloy
git ls-files '*.als'
```

| found, in this order | do |
| --- | --- |
| a model in another checked language (TLA+, Quint, Lean) | use it and the checker the repo runs it with |
| no `alloy` on PATH | say so, name where to get it (alloytools.org), and stop before writing anything; never check a model by reading it |
| `*.als` files | use their layout; read the model covering the change |
| none | initialise `spec/<module>/model.als` and `spec/<module>/check.als` |

## 2. Write or edit the model

`model.als` holds what the system is; `check.als` holds what must hold of it.

```alloy
module model

sig Thing { ... }

fact Wellformed { ... }            -- what the system guarantees by construction

pred step[...] { ... }             -- one operation
```

```alloy
open model

assert KeepsInvariant { ... }      -- what the change must not break
check KeepsInvariant for 3

run step for 3                     -- shows the model has an instance
```

- `model.als` has no commands; `check.als` has the asserts, the `check`s and at least one `run`.
- Name each `check` for what holds.
- A value is not modelled: `Int` is only as wide as the scope says (default `4 Int`, -8..7), wraps silently, has no reals, and cannot solve a 24-bit colour. Model its order or a small integer with `but N Int` set wide enough; the value itself goes to `test`.

## 3. Check

```sh
out=$(mktemp -d)/alloy
alloy exec -f -q -o "$out" spec/<module>/check.als && ls "$out"
```

| in `$out` | the `check` |
| --- | --- |
| `<Check>-solution-0.md` | found a counterexample; the file is it |
| no file for it | holds within its scope |
| `<Run>-solution-0.md` | the `run` found an instance; none means the facts contradict |
| nothing, and a non-zero exit | the model did not parse; read the error |

- Re-run `check.als` after each edit to either file.
- Start at `for 3` and raise the scope while each check finishes within a minute; report the scope each ran at.
- Read [alloy](references/alloy.md) § Running before the first run.

## 4. Check the code against the model

Each `pred` is an operation: its guard is a precondition the code checks before the effect, and its effect the only state it changes. Each `fact` and `assert` is an invariant the code never breaks. For each, name the code that enforces it and the test that fails when that code is removed; one with neither is a gap: report it.

Before trusting a green check, read [alloy](references/alloy.md) § A check green without its rule.
