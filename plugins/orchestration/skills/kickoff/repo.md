# Repo: GitHub and git

Issues live in the repository the work lands in; a parent spanning repositories goes on the repository the leader runs in. The checkout is the clone the leader works from, and the default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

| verb | command |
| --- | --- |
| `file` | parent: `gh issue create -R <repo> --title "<verb-first>" --body-file -`; issue: `gh label create effort:<effort> -R <repo> --force`, then the same create with `--parent <parent-url> --label effort:<effort>` |
| `checkout` | `git -C <checkout> fetch origin && git -C <checkout> worktree add --detach <checkout>/.claude/worktrees/<topic>-<issue> origin/<default>` |
| `claim` | `git fetch origin && ! git ls-remote --exit-code origin 'refs/heads/*-<issue>' && git switch -c <branch> origin/<default> && git push -u origin <branch>`, the branch named after the worktree; a branch found is yours only when this checkout is on it. Then `cp "$(command -v default-branch-guard)" "$(git rev-parse --path-format=absolute --git-path hooks)/pre-commit"`, unless a pre-commit is there already, which stays |
| `pr` | `gh pr create --base <default> --head <branch> --title "<verb-first>" --body "Closes #<issue>"` |
| `merge` | `gh pr merge <pr> --squash --match-head-commit <sha>`, with the sha from `gh pr view <pr> --json headRefOid -q .headRefOid` |
| `clean` | for each worker `git -C <checkout> worktree remove <worktree>`, `git -C <checkout> branch -D <branch>` and `git -C <checkout> push origin --delete <branch>`, the branch being merged by squash; then `git -C <checkout> pull --ff-only` |

A topic is 2-4 lowercase words joined by hyphens.
