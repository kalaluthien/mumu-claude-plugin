# Landing git

A change is a branch of the repository, filed and merged in local git by `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-landing.py`, the project's landing; the merge pushes the base to `origin`, so no GitHub pull request stands between a branch and the base. Each change is a record in the main checkout's `.teamwork/changes`, excluded from commits, numbered apart from the board's issues.

| operation | how |
| --- | --- |
| `branch` | [add-worktree.py](../../scripts/add-worktree.py) `<name> <base> [<branch>]`, which puts it under the main checkout's `.claude/worktrees/` from any folder of the checkout |
| `push` | nothing for the branch: every worktree shares the repository's branches |
| `change` | `use-landing.py change <branch> <title> <body-file> [<base>]`, the body citing its issue; it prints the change's url, whose number the heartbeat names |
| `judge` | the judge reads the change at its sha by `git diff <base>...<sha>` and `git show <sha>:<path>`, with no fetch |
| `merge` | `use-landing.py merge <change> <sha>`, the sha the judge approved, which it refuses when the branch tip moved; it squashes the head onto the base as one commit, tags it and pushes the tags with that commit to `origin`'s base as one atomic fast-forward (see Release hook), and only then moves the local base and the worktree that has it checked out; a repository with no `origin` skips the push |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...` |

- **Release hook**: when the merge commit tracks `.github/plan-release.py`, the merge runs that script as `plan-release.py <base sha> <merge sha>`, tags the merge commit with each tag line it prints and pushes them with the base; a non-zero exit refuses the merge with its stderr, nothing tagged or pushed. Bump what the repository's rules say before the `judge`, since the merge cannot change the head the judge approved.
- **Base refs**: where a playbook writes `origin/<base>`, write `<base>`, and pass `run-criteria.py --base --ref <base>`, since the local base is the one the merge moved.
- **Refused merge**: a merge that conflicts, that would overwrite uncommitted files in the base's worktree, or whose push `origin` refuses, changes nothing and names the cause. After a conflict or a refused push, pull the base, rebase and judge the new tip; for uncommitted files, ask your manager by `BLOCKED:`.
