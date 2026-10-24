# Landing: GitHub

A change is a git branch merged by a GitHub pull request.

| operation | how |
| --- | --- |
| `branch` | `git worktree add -b <name> .claude/worktrees/<name> origin/<base>` in the checkout |
| `push` | `git push -u origin <branch>`, the branch named, never `HEAD:<branch>`, so a worker's branch has an upstream and one command form |
| `change` | `gh pr create --base <base> --title <title> --body-file <file>`, the body citing its issue |
| `judge` | the judge reads the change at its sha by `git fetch origin`, `git diff origin/<base>...<sha>` and `git show <sha>:<path>` |
| `merge` | `gh pr merge <n> --squash` |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...` |

- **Live checkout**: after a merge `AGENTS.md`'s `Live checkout` names, `git -C <live checkout> pull --ff-only` before `reload`.
