# Landing: GitHub

A change is a git branch merged by a GitHub pull request.

| operation | how |
| --- | --- |
| `branch` | `git worktree add -b <name> .claude/worktrees/<name> origin/<base>` in the checkout |
| `change` | `gh pr create --base <base> --title <title> --body-file <file>`, the body citing its issue |
| `judge` | the judge reads the change at its sha by `git fetch origin` (and `git fetch origin refs/pull/<n>/head` for one from a fork), `git diff origin/<base>...<sha>` and `git show <sha>:<path>` |
| `merge` | `gh pr merge <n> --squash` |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...` |

- **Live checkout**: after a merge `AGENTS.md`'s `Live checkout` names, `git -C <live checkout> pull --ff-only` before `reload`.
