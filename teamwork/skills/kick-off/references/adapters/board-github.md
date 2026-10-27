# Board: GitHub

The board is the repository's GitHub issues, through `gh`, a body always by `--body-file`, its file written before the command, since a hook refuses `--body` and `-b` when the repository's `.teamwork/settings.json` sets `"refuse": true`, and else warns.

| operation | how |
| --- | --- |
| `read` | `gh issue view <n> --json title,body,comments,labels,state`; a pull request by `gh pr view`, also `headRefOid` |
| `comment` | `gh issue comment <n> --body-file <file>`, or `gh pr comment` |
| `file` | `gh issue create --title <title> --label <label> --body-file <file>`, each label first `gh label create <label> --force` |
| `edit` | the body by [edit-issue-body.py](../../scripts/edit-issue-body.py) `<issue> <diff-file> "DECIDED: <why>"`; the title by `gh issue edit <n> --title <title>` |
| `resolve` | `gh issue close <n> --reason completed --comment "REPORTED: <summary>"`, or `--reason "not planned"` |
| `reopen` | `gh issue reopen <n>` |
| `decide` | `comment` a `DECIDED:` |
| `order` | `gh api -X POST repos/<repo>/issues/<later>/dependencies/blocked_by -F issue_id=<earlier's id>`; ids by `gh api repos/<repo>/issues/<n> -q .id` |
| `nest` | `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py nest <issue> <task>` |
| `label` | `gh issue edit <n> --add-label <label>` or `--remove-label <label>`, the label first `gh label create <label> --force` |

- **Cloud**: GraphQL is refused there (`HTTP 403`), so a remote worker does each `gh issue` form above by its `gh api` REST form: read by `gh api repos/<repo>/issues/<n>` and `…/comments`; comment by `gh api -X POST repos/<repo>/issues/<n>/comments -F body=@<file>`; file by `gh api -X POST repos/<repo>/issues -f title=<title> -F body=@<file> -f 'labels[]=<label>'`; the title by `gh api -X PATCH repos/<repo>/issues/<n> -f title=<title>`; resolve by `gh api -X PATCH repos/<repo>/issues/<n> -f state=closed -f state_reason=completed` after its `REPORTED:` comment; reopen by `gh api -X PATCH repos/<repo>/issues/<n> -f state=open`; label by `gh api -X POST repos/<repo>/issues/<n>/labels -f 'labels[]=<label>'`, or `-X DELETE …/labels/<label>`. A `[check]` a remote worker runs reads by these REST forms too, never `gh issue view` or `gh pr list`.
- **Trusted**: an author whose association is `OWNER`, `MEMBER` or `COLLABORATOR`.
- **Scope labels**: `gh label list --search scope:`.
- **Default branch**: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.
