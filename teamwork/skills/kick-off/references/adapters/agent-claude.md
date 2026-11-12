# Agent Claude

A subagent is an `Agent` call of a Claude Code session.

| operation | how |
| --- | --- |
| `delegate` | an `Agent` call naming its `model` by tier, since one without runs on yours: `open` `fable`, `deep` `opus`, `mid` `sonnet`, `light` `haiku`; a code search or a read of named files may use `Explore` |
| `compact` | prompt yourself `/compact Keep only: <what>.` |

- **Tier of a session**: `start` passes the tier's model as `--model` and the effort as `--effort`.
- **Publishing tool**: `Artifact`, which a manager keeps on by `--allow Artifact`.
- **Refused step**: auto mode refuses by the outcome, not the form, and no `DECIDED:` lifts it: it refuses `rm` of untracked or ignored files outside a worktree, `reset --hard` or `merge --ff-only` of a clean worktree, and a `close` of a live session (`Interfere With Workloads`), so when the base moves before your first commit, open a new branch worktree from `origin/<base>`. Hand the owner a refused step at once as `! <command>`; for a rule, guard or agent file, `! git -C <worktree> apply <patch-path>` of a scratchpad patch, first checked by `git apply --check`. A refused, rejected or interrupted call may still have run: read its effect back, such as the board, before redoing or dropping it; reuse what landed, edited to the owner's latest word, and tell the owner it ran.

## Tier of a worker

Take the first row that fits, its effort raised to `high` for a high risk. One test splits `open` from `deep`: the owner's words and the repository say what done is and how to reach it, or they do not.

| tier | model | effort | the root |
| --- | --- | --- | --- |
| `light` | `haiku` | `medium` | is a mechanical edit to a fixed spec |
| `open` | `fable` | `medium` | has no known answer or leaves its meaning open, needs a migration strategy that is not yet chosen (its order, its rollback), or is a UX or UI design with no layout words |
| `deep` | `opus` | `medium` | has a known approach but needs splitting into tasks or a design settled by reading the code, such as a migration whose strategy is given |
| `mid` | `sonnet` | `medium` | is any other work |

A worker moves up one tier, `mid` to `deep` to `open`, as the manager's **Swap up** says.

## Tier by work

Each line names the tier, then the effort:

- planning, debugging: `deep`, `high`
- design, experiment, web search, an edit needing judgment, reading captures: `mid`, `medium`
- a mechanical edit to a fixed spec: `light`, `medium`
- writing tests; scoring or marking a sample by a rubric: `mid`, `low`
- running tests or a long check, reporting only failures; code search, reading named files with no judgment: `light`, `low`
