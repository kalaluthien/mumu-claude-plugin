# Landing git

A change is a branch of the repository, filed and merged in local git by [use-landing.py](landing-git/scripts/use-landing.py), the project's landing; the merge pushes the base to `origin`. Each change is numbered apart from the board's tasks.

| operation | how |
| --- | --- |
| `branch` | [add-worktree.py](../../scripts/add-worktree.py) `<name> <base> [<branch>]` |
| `push` | nothing for the branch: every worktree shares the repository's branches |
| `change` | `use-landing.py change <branch> <title> <body-file> [<base>]`, the body citing its task; it prints the change's url, whose number the heartbeat names |
| `judge` | the judge reads the change at its sha by `git diff <base>...<sha>` and `git show <sha>:<path>`, with no fetch |
| `merge` | `use-landing.py merge <change> <sha>`, the sha the judge approved, which it refuses when the branch tip moved and its diff from where it left the base, line numbers and `index` lines aside, is not the tip's; it pushes the merge to `origin`'s base as one atomic fast-forward, and only then moves the local base and the worktree that has it checked out; a repository with no `origin` skips the push |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...` |

- **Release hook**: when the merge commit tracks `.github/plan-release.py`, the merge runs that script as `plan-release.py <base sha> <merge sha>`, tags the merge commit with each tag line it prints and pushes them with the base; a non-zero exit refuses the merge with its stderr, nothing tagged or pushed.
- **Base refs**: where a playbook writes `origin/<base>`, write `<base>`, and pass `run-criteria.py --base --ref <base>`, since the local base is the one the merge moved.
- **Refused merge**: a merge that conflicts, that would overwrite uncommitted files in the base's worktree, or whose push `origin` refuses, changes nothing and names the cause. After a conflict or a refused push, pull the base and rebase, then merge the approved sha again when the rebase left the change's diff the same, else judge the new tip; for uncommitted files, ask your manager by `BLOCKED:`. A merge that `origin` took but the local base did not is merged and its change closed: run the step its error names to bring the local base up to `origin`, and judge nothing again.
