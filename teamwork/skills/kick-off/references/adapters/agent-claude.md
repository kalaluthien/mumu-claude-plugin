# Agent: Claude Code

| operation | how |
| --- | --- |
| `delegate` | an `Agent` call naming its `model` by tier, since one without runs on yours: `deep` `opus`, `mid` `sonnet`, `light` `haiku`; a code search or a read of named files may use `Explore` |
| `compact` | prompt yourself `/compact Keep only: <what>.` |

- **Tier of a session**: `start` passes the tier's model as `--model` and the effort as `--effort`.
- **Publishing tool**: `Artifact`, which a manager keeps on by `--allow Artifact`.
- **Refused step**: auto mode refuses by the outcome, not the form, and no `DECIDED:` lifts it: it refuses `rm` of untracked or ignored files outside a worktree, and `reset --hard` or `merge --ff-only` of a clean worktree, so when the base moves before your first commit, open a new branch worktree from `origin/<base>`. Hand the owner a refused step at once as `! <command>`, by `PushNotification` when away; for a rule, guard or agent file, `! git -C <worktree> apply <patch-path>` of a scratchpad patch, first checked by `git apply --check`. A call the owner rejected or interrupted may still have run: read its effect back, such as the board, before redoing or dropping it, and reuse what landed.
- **Paths**: a `SKILL.md` names a file as `${CLAUDE_PLUGIN_ROOT}/<path>`; a playbook link is relative to the playbook.
