# Landing GitHub

A change is a git branch merged by a GitHub pull request, for a repository whose rules ask for one; the board stays in local refs.

| operation | how |
| --- | --- |
| `branch` | [add-worktree.py](../../scripts/add-worktree.py) `<name> origin/<base> [<branch>]` |
| `push` | `git push -u origin <branch>`, never `HEAD:<branch>`, so a worker's branch has an upstream |
| `change` | `gh pr create --base <base> --title <title> --body-file <file>`, the body citing its task; then read the pull request's files and head sha by `gh pr view <n> --json files,headRefOid` before the `judge` |
| `judge` | the judge reads the change at its sha by `git fetch origin`, `git diff origin/<base>...<sha>` and `git show <sha>:<path>` |
| `merge` | `gh pr merge <n> --squash --match-head-commit <sha>`, the sha the judge approved, which `gh` refuses when the pull request head moved; releasing as the repository's rules say |
| `remove` | [remove-worktree.py](../../scripts/remove-worktree.py) `<name>...`; a local change and a pull request share the `#n` list of a merged line, told apart by their size |

- **Live checkout**: after a merge the repository's rules say needs a refresh, `git -C <live checkout> pull --ff-only` before `reload`.
