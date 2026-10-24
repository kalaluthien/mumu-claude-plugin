# Landing: local git

A change is a branch of a repository with no remote, filed and merged by `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-landing.py`, picked by `TEAMWORK_LANDING=git`, set in the project's settings `env` beside `TEAMWORK_BOARD=files` so every session, hook and monitor reads it. Each change is a record in the git common folder's `teamwork/changes`, numbered apart from the board's issues.

| operation | how |
| --- | --- |
| `branch` | `git worktree add -b <name> .claude/worktrees/<name> <base>` in the checkout |
| `push` | nothing: every worktree shares the repository's branches |
| `change` | `use-landing.py change <branch> <title> <body-file> [<base>]`, the body citing its issue; it prints the change's url, whose number the heartbeat names |
| `judge` | the judge reads the change at its sha by `git diff <base>...<sha>` and `git show <sha>:<path>`, with no fetch |
| `merge` | `use-landing.py merge <change> <sha>`, the sha the judge approved, which it refuses when the branch tip moved; it squashes the head onto the base as one commit and fast-forwards the worktree that has the base checked out |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...` |

- **Base refs**: where a playbook writes `origin/<base>`, write `<base>`, and pass `run-criteria.py --base --ref <base>`, since there is no `origin`.
- **Refused merge**: a merge that conflicts, or that would overwrite uncommitted files in the base's worktree, changes nothing. Rebase and judge the new tip; for those files, ask your manager by `BLOCKED:`.
