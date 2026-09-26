# Repo: GitHub and git

A goal and its tasks live in its leader's repository, the one its checkout clones. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, and `<hooks>` is `git -C <checkout> rev-parse --path-format=absolute --git-path hooks`.

A worker's worktree goes in its leader's own checkout only, never in another repository's clone.

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state,parent`, or `gh pr view <url> --json title,body,comments,headRefOid`; what a goal holds is its sub-issues, `gh api repos/<repo>/issues/<n>/sub_issues`, each read the same way down to the tasks |
| `file` | root goal: `gh label create kind:goal -R <repo> --force`, then `gh issue create -R <repo> --title "<title>" --label kind:goal --body-file -`; a goal under a goal: the same with `--parent <goal-url>`; task: `gh label create effort:<effort> -R <repo> --force`, `<effort>` `low` or `medium` unless the owner named another, then `gh issue create -R <repo> --title "<title>" --label kind:task --label effort:<effort> --body-file -`, with `--parent <goal-url>` unless it is a root task |
| `order` | `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>`, `<id>` the blocker's `gh api repos/<owner>/<repo>/issues/<m> -q .id`, in this repository or another |
| `comment` | `gh issue comment <url> --body-file -` |
| `decide` | `decide.py <url> [--criteria <file>] < <decision>`: posts `DECIDED: <decision>`, and with `--criteria` first replaces the body's `## Definition of done` by the file's lines |
| `resolve` | `gh issue close <url> --reason completed --comment "<summary>"` |
| `stop` | `gh issue close <url> --reason "not planned" --comment "<reason>"`, then `gh pr ready --undo <pr-url>` for its open pull request |
| `claim` | `git fetch origin && ! git ls-remote --exit-code origin refs/heads/<branch> && git switch -c <branch> origin/<default> && git push -u origin <branch>`, the branch named after the worktree; a branch found is yours only when this checkout is on it |
| `pr` | `gh pr create --base <default> --head <branch> --title "<title>" --body-file -`; later `gh pr edit <pr> --body-file -` |
| `merge` | `merge.py <pr-url>`: squash-merges pinned to the head only when a comment or review opens `APPROVED: <head>`; a raw `gh pr merge` is refused |
| `clean` | for each worker `git -C <checkout> worktree remove <worktree>`, `git -C <checkout> branch -D <branch>` and `git -C <checkout> push origin --delete <branch>`, the branch being merged by squash; then `git -C <checkout> pull --ff-only`, and remove each of `<hooks>/pre-commit` and `<hooks>/pre-push` that `cmp -s` finds equal to the guard, as `rm "${H:?}/${h:?}"` with `H=<hooks>`, since Claude Code refuses an `rm` whose target could expand empty; last `tab-sweep.py <checkout>`, which closes every tab whose panes run no agent and sit under `<checkout>/.claude/worktrees/`, so no worker tab outlives its session |

## Traps

- `file`: `--parent` creates the issue even when the link fails, so relink the printed url with `gh issue edit <url> --parent <goal-url>`, never create it again.
- `pr` and `merge`: an error such as `GraphQL: Something went wrong` may still have landed, so `read` the state before retrying; just after a push `headRefOid` can name the old head, which `git ls-remote origin refs/heads/<branch>` does not.
- CI: a pull request whose `gh pr view --json mergeable` is `CONFLICTING` gets no run, and a job with `needs` is absent from `gh pr checks` until they finish, so wait in the foreground with `gh run watch <id> --exit-status`.
