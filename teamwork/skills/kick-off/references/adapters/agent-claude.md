# Agent: Claude Code

| operation | how |
| --- | --- |
| `delegate` | an `Agent` call naming its `model` by tier, since one without runs on yours: `deep` `opus`, `mid` `sonnet`, `light` `haiku`; a code search or a read of named files may use `Explore` |
| `compact` | prompt yourself `/compact Keep only: <what>.` |

- **Tier of a session**: `start` passes the tier's model as `--model` and the effort as `--effort`.
- **Publishing tool**: `Artifact`, which a manager keeps on by `--allow Artifact`.
- **Refused step**: when auto mode refuses a step, the command you hand the owner is `! <command>`, by `PushNotification` when away; for a rule, guard or agent file, `! git -C <worktree> apply <patch-path>` of a scratchpad patch, first checked by `git apply --check`.
- **Paths**: a `SKILL.md` names a file as `${CLAUDE_PLUGIN_ROOT}/<path>`; a playbook link is relative to the playbook.
