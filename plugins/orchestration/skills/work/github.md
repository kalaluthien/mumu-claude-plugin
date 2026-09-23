# git and gh, for the worker

| step | command |
| --- | --- |
| default branch | `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` |
| claim | `git fetch origin && ! git ls-remote --exit-code origin refs/heads/<branch> && git switch -c <branch> origin/<default> && git push -u origin <branch>` |
| arm pre-commit | `h=$(git rev-parse --path-format=absolute --git-path hooks)/pre-commit; [ -e "$h" ] \|\| ln -s "$(command -v default-branch-guard)" "$h"`; an existing hook is the repo's own: leave it and say so in the PR |
| mission | `f=$(mission path)`, then write the 3-5 lines to `$f` |
| PR | `gh pr create --base <default> --head <branch> --title "<verb-first>" --body "Closes #<issue>"` |
| head sha | `gh pr view <pr> --json headRefOid -q .headRefOid` |
| merge | `gh pr merge <pr> --squash --match-head-commit <sha>` |
| blocked | `gh issue comment <issue> --body "BLOCKED: <question>"`; leader pane from `herdr agent list`; `herdr agent prompt <pane> "BLOCKED on <issue-url>"` |

Branch name: `<issue>-<topic>`, topic 2-4 lowercase words joined by `-`.
