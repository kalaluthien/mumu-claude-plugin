# Agent Claude

A subagent is an `Agent` call of a Claude Code session.

| operation | how |
| --- | --- |
| `delegate` | an `Agent` call naming its `model` by tier, since one without runs on yours: `open` `fable`, `deep` `opus`, `mid` `sonnet`, `light` `haiku`; a code search or a read of named files may use `Explore` |
| `compact` | prompt yourself `/compact Keep only: <what>.` |

- **Publishing tool**: `Artifact`.
- **Refused step**: auto mode refuses by the outcome, not the form, and no `DECIDED:` lifts it: it refuses `rm` of untracked or ignored files outside a worktree, `reset --hard` or `merge --ff-only` of a clean worktree, and a `close` of a live session (`Interfere With Workloads`), so when the base moves before your first commit, open a new branch worktree from `origin/<base>`. Hand the owner a refused step at once as `! <command>`; for a rule, guard or agent file, `! git -C <worktree> apply <patch-path>`, first checked by `git apply --check`. A refused, rejected or interrupted call may still have run: read its effect back, such as the board, before redoing or dropping it; reuse what landed, edited to the owner's latest word, and tell the owner it ran.

## Tier of a worker

Lean to the cheapest row that fits: `mid` (sonnet) builds to a known approach, `light` (haiku) does a fixed edit, and `deep` (opus) and `open` (fable) are kept for a design not yet settled and hard judgement. Take the first row that fits, its effort raised to `high` for a high risk. One test splits `open` from `deep`: the owner's words and the repository say what done is and how to reach it, or they do not.

| tier | model | effort | the root |
| --- | --- | --- | --- |
| `light` | `haiku` | `medium` | is a mechanical edit to a fixed spec |
| `open` | `fable` | `medium` | has no known answer or leaves its meaning open, needs a migration strategy that is not yet chosen (its order, its rollback), or is a UX or UI design with no layout words |
| `deep` | `opus` | `medium` | needs a design that only reading the code settles, or a split into tasks whose order is a judgement, such as the order of a migration's steps |
| `mid` | `sonnet` | `medium` | is any other work, a known approach across several tasks included |

A tier is a lean, not a cap: a worker moves up one tier, `mid` to `deep` to `open`, when the work proves harder, as the manager's **Swap up** says.

## Tier by work

Each line names the tier, then the effort; lean to the line's tier and raise it one step when its result falls short:

- planning, a design not yet settled, debugging a cause not yet found: `deep`, `high`
- an experiment, a web search, an edit needing judgment, reading captures, a probe: `mid`, `medium`
- a mechanical edit to a fixed spec: `light`, `medium`
- writing tests; scoring or marking a sample by a rubric: `mid`, `low`
- running tests or a long check, reporting only failures; code search, reading named files with no judgment: `light`, `low`
