# Repo: GitHub and git

A goal's issues live in its leader's repository, the one its checkout clones. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, and `<hooks>` is `git -C <checkout> rev-parse --path-format=absolute --git-path hooks`.

A worker's worktree goes in its leader's own checkout only, never in another repository's clone.

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,parent`, or `gh pr view <url> --json title,body,comments,headRefOid`; a goal's issues are its sub-issues, `gh api repos/<repo>/issues/<parent>/sub_issues` |
| `file` | parent: `gh issue create -R <repo> --title "<title>" --body-file -`; issue: `gh label create effort:<effort> -R <repo> --force`, then the same create with `--parent <parent-url> --label effort:<effort>` |
| `comment` | `gh issue comment <url> --body-file -` |
| `resolve` | `gh issue close <url> --comment "<summary>"` |
| `handoff` | `gh issue transfer <url> <owner>/<target-repo>`, which prints the new url; then `prompt` the target project's leader `see <new-url>` |
| `checkout` | `git -C <checkout> fetch origin && git -C <checkout> worktree add --detach <checkout>/.claude/worktrees/<topic>-<issue> origin/<default>`; unless `git -C <checkout> config core.hooksPath` is set, copy `$(command -v default-branch-guard.sh)` to each of `<hooks>/pre-commit` and `<hooks>/pre-push` not there yet |
| `claim` | `git fetch origin && ! git ls-remote --exit-code origin 'refs/heads/*-<issue>' && git switch -c <branch> origin/<default> && git push -u origin <branch>`, the branch named after the worktree; a branch found is yours only when this checkout is on it |
| `pr` | `gh pr create --base <default> --head <branch> --title "<title>" --body-file -`; later `gh pr edit <pr> --body-file -` |
| `merge` | `gh pr merge <pr-url> --squash --match-head-commit <approved sha>` |
| `clean` | for each worker `git -C <checkout> worktree remove <worktree>`, `git -C <checkout> branch -D <branch>` and `git -C <checkout> push origin --delete <branch>`, the branch being merged by squash; then `git -C <checkout> pull --ff-only`, and remove each of `<hooks>/pre-commit` and `<hooks>/pre-push` that `cmp -s` finds equal to the guard |
