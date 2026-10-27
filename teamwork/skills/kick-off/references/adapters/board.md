# Board

Each operation is one call of `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py`, on any board, with each text in a file written first. It works on the board `TEAMWORK_BOARD` names, else GitHub.

| operation | how |
| --- | --- |
| `read` | `use-board.py read <n>` |
| `comment` | `use-board.py comment <n> <body-file>` |
| `file` | `use-board.py file <title> <body-file> [label...]` |
| `edit` | `use-board.py edit <n> <diff-file> "DECIDED: <why>"`, which runs [edit-issue-body.py](../../scripts/edit-issue-body.py); the title by `use-board.py title <n> <title>` |
| `resolve` | `use-board.py resolve <n> <summary-file> [--not-planned]`, the file's text opening with `REPORTED:` |
| `reopen` | `use-board.py reopen <n>` |
| `decide` | `use-board.py decide <n> <body-file>`, the file's text opening with `DECIDED:` |
| `order` | `use-board.py order <later> <earlier>` |
| `nest` | `use-board.py nest <issue> <task>` |
| `label` | `use-board.py label <n> <name> [--remove]` |

## GitHub

The board is the repository's GitHub issues, read and written by `gh api` REST calls, which also work in a cloud session, where GraphQL is refused (`HTTP 403`).

- **Pull request**: its head by `gh pr view <n> --json headRefOid`.
- **Cloud checks**: a `[check]` a remote worker runs reads by `gh api repos/<repo>/issues/<n>` and `…/comments` too, never `gh issue view` or `gh pr list`.
- **Trusted**: an author whose association is `OWNER`, `MEMBER` or `COLLABORATOR`.
- **Scope labels**: `gh label list --search scope:`.
- **Default branch**: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

## Files

The board is a folder of plain files, `TEAMWORK_BOARD_DIR`, else `.teamwork/board` in the main checkout (one board per project, the same for every worktree, kept out of commits by the line the first read adds to `.git/info/exclude`, which also moves a board an older version kept under `.git/teamwork`; outside a repository, `~/.claude/teamwork/board`), picked by `TEAMWORK_BOARD=files`: each issue is `<n>/` with `issue.json`, `body.md` and `comments/<k>.md`.

- **Trusted**: every record, since only local users write the folder.
- **Scope labels**: an issue labelled `scope:<project>`.
- **Default branch**: the landing adapter's, not the board's.
