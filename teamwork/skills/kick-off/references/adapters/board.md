# Board

Each operation is one call of `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py`, on any board, with each text in a file written first. It works on the board `TEAMWORK_BOARD` names, else the git board. A verb that writes more than one record, such as a body edit with its DECIDED comment or a resolve with its parent's close, lands as one commit on a board that can, so a reader never sees half of it.

| operation | how |
| --- | --- |
| `read` | `use-board.py read <n>` |
| `comment` | `use-board.py comment <n> <body-file>` |
| `file` | `use-board.py file <title> <body-file> [label...] [--scope <folder>]` |
| `edit` | `use-board.py edit <n> <diff-file> "DECIDED: <why>" --base <sha>`, the `body sha` `read` printed, refused when the body has changed since; it runs [edit-issue-body.py](../../scripts/edit-issue-body.py); the title by `use-board.py title <n> <title>` |
| `resolve` | `use-board.py resolve <n> <summary-file> [--not-planned]`, the file's text opening with `REPORTED:` |
| `reopen` | `use-board.py reopen <n>` |
| `decide` | `use-board.py decide <n> <body-file>`, the file's text opening with `DECIDED:` |
| `label` | `use-board.py label <n> <name> [--remove]` |

## GitHub

The board is the repository's GitHub issues, picked by `TEAMWORK_BOARD=github`, read and written by `gh api` REST calls, whose quota runs out apart from GraphQL's:

- **GraphQL refused**: REST still works in a cloud session, where GraphQL answers `HTTP 403`, and once GraphQL is spent; trust a call's `already exceeded` over `gh api rate_limit`.
- **REST spent**: scripts fail with `could not read task`; wait for `gh api rate_limit -q .resources.core.reset`, or comment and edit by `gh issue comment` and `gh issue edit`, which use GraphQL.
- **Read cost**: every read spends quota, a `404` included, but a `304` to `If-None-Match`, on which `gh api -i` exits 1; read a list, such as `search/issues`, rather than probe items.
- **GraphQL cost**: a query costs per connection asked for; `rateLimit(dryRun: true) { cost }` prices it without its data, and a `gh` first on `PATH` that fails `api graphql`, `issue`, `pr`, `repo` and `label` proves a script asks none.

- **Pull request**: its head by `gh pr view <n> --json headRefOid`.
- **Cloud checks**: a `[check]` a remote worker runs reads by `gh api repos/<repo>/issues/<n>` and `…/comments` too, never `gh issue view` or `gh pr list`.
- **Trusted**: an author whose association is `OWNER`, `MEMBER` or `COLLABORATOR`.
- **Scope labels**: `gh label list --search scope:`, rechecked before concluding none carries a label, since a search right after its rename can read empty for about 10 s, and outside a checkout given `-R <owner>/<repo>` read from `git remote`, never built from a folder name.
- **Default branch**: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

## Files

The board is a folder of plain files, `TEAMWORK_BOARD_DIR`, else `.teamwork/board` in the main checkout (one board per project, the same for every worktree, kept out of commits by the line the first read adds to `.git/info/exclude`, which also moves a board an older version kept under `.git/teamwork`; outside a repository, `~/.claude/teamwork/board`), picked by `TEAMWORK_BOARD=files`: each issue is `<n>/` with `issue.json`, `body.md` and `comments/<k>.md`, or `<folder>/<n>/` when it belongs to a folder of the repository.

- **Trusted**: every record, since only local users write the folder.
- **Scope**: an issue's folder, below.
- **Default branch**: the landing adapter's, not the board's.

## Git

The board is the commit `refs/teamwork-blackboard` names in the current folder's repository, the default board: one ref per repository, one commit per write, shared by every worktree of the project. A write outside a repository refuses.

- **Scope**: an issue lives at `<folder>/<n>/` of the ref's tree, `<folder>` a path from the repository root such as `teamwork`, and at `<n>/` when its project is the root. A project's folder is the top-level folder named like it, else the root; no setting names it. A project reads its folder and below, the root project only the root's own issues. Issue numbers are unique across the repository, so `read <n>` needs no folder. `file --scope <folder>` files into a folder, refused when the repository has no such folder, and with no `--scope` a manager files into its own project's folder, any other session into the root. An issue's url is `git+file://<git common dir>/refs/teamwork-blackboard/<folder>/<n>`.

- **History**: `git log --stat refs/teamwork-blackboard` shows every write; `git show refs/teamwork-blackboard:<folder>/<n>/body.md` reads one file.
- **Moving a board**: run `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/copy-board.py files git` (or `github git`) in the checkout before any other write to it; it copies into an empty board only, and each comment copied between local boards takes the copy's time. From GitHub it copies every issue, closed ones too, each under the top-level folder its `scope:<folder>` label names (and without that label), else at the root with its labels, with each comment's GitHub time, skips an untrusted author's body or comment, rewrites GitHub issue and comment urls to the git board's, and sets a number floor above the highest issue or pull-request number. Then `compare-boards.py <project>` prints `PASS` when the pane, `list-decisions.py` and the heartbeat show the same on both boards.
- **Stale lock**: a write that finds `.git/refs/teamwork-blackboard.lock` older than 10 s refuses, naming it; remove that file once no board write runs.
- **Local only**: a plain clone, fetch or push leaves `refs/teamwork-blackboard` behind, so the board stays on this machine unless pushed by name; `git push --mirror` sends it.
- **Trusted** and **Default branch**: as on the files board.
