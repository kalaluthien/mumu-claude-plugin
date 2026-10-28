# Agent: Claude Code

| operation | how |
| --- | --- |
| `delegate` | an `Agent` call naming its `model` by tier, since one without runs on yours: `deep` `opus`, `mid` `sonnet`, `light` `haiku`; a code search or a read of named files may use `Explore` |
| `compact` | prompt yourself `/compact Keep only: <what>.` |

- **Tier of a session**: `start` passes the tier's model as `--model` and the effort as `--effort`.
- **Publishing tool**: `Artifact`, which a manager keeps on by `--allow Artifact`.
- **Refused step**: when auto mode refuses a step, the command you hand the owner is `! <command>`, by `PushNotification` when away; for a rule, guard or agent file, `! git -C <worktree> apply <patch-path>` of a scratchpad patch, first checked by `git apply --check`.
- **Paths**: a `SKILL.md` names a file as `${CLAUDE_PLUGIN_ROOT}/<path>`; a playbook link is relative to the playbook.
- **Refused delete**: auto mode refuses `rm` of untracked or ignored files outside a worktree even under a `DECIDED:`, so hand the owner the `! rm …` line in the first ask.
- **Base moved**: when the base moves before your first commit, open a new branch worktree from `origin/<base>`, since auto mode refuses `reset --hard` and `merge --ff-only` of a clean worktree.
- **Rejected call**: a call with an outward effect, such as an issue, a comment or a push, that the owner rejected or interrupted may still have run: read the board back before redoing or dropping it, and reuse what landed.
