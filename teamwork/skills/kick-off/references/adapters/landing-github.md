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

- **Cloud**: a remote worker works in its session's own checkout, so `branch` is its `claude/<slug>` branch or one it names, with no worktree; `change` is `gh api -X POST repos/<repo>/pulls -f head=<branch> -f base=<base> -f title=<title> -F body=@<file>` and `merge` is `gh api -X PUT repos/<repo>/pulls/<n>/merge -f merge_method=squash -f sha=<head sha>`, since GraphQL is refused there; `remove` is not needed, since the checkout ends with the session.
- **Live checkout**: after a merge `AGENTS.md`'s `Live checkout` names, `git -C <live checkout> pull --ff-only` before `reload`.
- **Commit**: join commit, amend and push by `&&`, one message source (`-F <file>` alone), since a failed commit followed by `--amend` rewrites the base's tip; after `push`, read the pull request's files and head sha before the `judge`.
