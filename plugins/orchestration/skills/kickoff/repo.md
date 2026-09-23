# Repo: GitHub and git

Issues live in the repository the work lands in; a parent spanning repositories goes on the repository the leader runs in. The checkout is the clone the leader works from, and the default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

| verb | command |
| --- | --- |
| `file` | parent: `gh issue create -R <repo> --title "<verb-first>" --body-file -`; issue: `gh label create effort:<effort> -R <repo> --force`, then the same create with `--parent <parent-url> --label effort:<effort>` |
| `checkout` | `git -C <checkout> fetch origin && git -C <checkout> worktree add --detach <checkout>/.claude/worktrees/<topic>-<issue> origin/<default>` |
| `claim` | `git fetch origin && ! git ls-remote --exit-code origin refs/heads/<branch> && git switch -c <branch> origin/<default> && git push -u origin <branch>`; a branch found is yours only when this checkout is on it. Then `ln -s "$(command -v default-branch-guard)" "$(git rev-parse --path-format=absolute --git-path hooks)/pre-commit"`, unless a pre-commit is there already: that one is the repository's own, so leave it and say so in the pull request |
| `pr` | `gh pr create --base <default> --head <branch> --title "<verb-first>" --body "Closes #<issue>"` |
| `merge` | `gh pr merge <pr> --squash --match-head-commit <sha>`, with the sha from `gh pr view <pr> --json headRefOid -q .headRefOid` |
| `clean` | `git -C <checkout> worktree remove <worktree>` for each worker, then `git -C <checkout> branch -D` each worker's branch, merged by squash |

A topic is 2-4 lowercase words joined by hyphens.
