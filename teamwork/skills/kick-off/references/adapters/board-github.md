# Board: GitHub

The board is the repository's GitHub issues, through `gh`, a body always by `--body-file`, its file written before the command, since a hook refuses `--body` and `-b`.

| operation | how |
| --- | --- |
| `read` | `gh issue view <n> --json title,body,comments,labels,state`; a pull request by `gh pr view`, also `headRefOid` |
| `comment` | `gh issue comment <n> --body-file <file>`, or `gh pr comment` |
| `file` | `gh issue create --title <title> --label <label> --body-file <file>`, each label first `gh label create <label> --force` |
| `edit` | the body by [edit-issue-body.py](../../scripts/edit-issue-body.py) `<issue> <diff-file> "DECIDED: <why>"`; the title by `gh issue edit <n> --title <title>` |
| `resolve` | `gh issue close <n> --reason completed --comment "REPORTED: <summary>"`, or `--reason "not planned"` |
| `decide` | `comment` a `DECIDED:` |
| `order` | `gh api -X POST repos/<repo>/issues/<later>/dependencies/blocked_by -F issue_id=<earlier's id>`; ids by `gh api repos/<repo>/issues/<n> -q .id` |
| `nest` | `gh api -X POST repos/<repo>/issues/<backlog>/sub_issues -F sub_issue_id=<task's id>` |
| `label` | `gh issue edit <n> --add-label <label>` or `--remove-label <label>`, the label first `gh label create <label> --force` |

- **Trusted**: an author whose association is `OWNER`, `MEMBER` or `COLLABORATOR`.
- **Scope labels**: `gh label list --search scope:`.
- **Default branch**: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.
