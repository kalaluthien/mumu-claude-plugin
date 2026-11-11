# Board

Each operation is one call of `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py`, with each text in a file written first by the Write tool, never a bare `cat >` in a chained call, which waits on stdin until the call times out. A verb that writes more than one record, such as a body edit with its DECIDED comment or a resolve with its parent's close, lands as one commit, so a reader never sees half of it.

| operation | how |
| --- | --- |
| `read` | `use-board.py read <n> [--as worker\|judge]` |
| `comment` | `use-board.py comment <n> <body-file>` |
| `file` | `use-board.py file <title> <body-file> [label...] [--scope <folder>]` |
| `edit` | `use-board.py edit <n> <body-file> "DECIDED: <why>" --base <sha>`, the whole new body, made from what `use-board.py read <n> --body` prints, and the `body sha` `read` printed, refused when the body has changed since; the title by `use-board.py title <n> <title>` |
| `resolve` | `use-board.py resolve <n> <summary-file> [--not-planned]`, the file's text opening with `REPORTED:` |
| `reopen` | `use-board.py reopen <n>` |
| `decide` | `use-board.py decide <n> <body-file>`, the file's text opening with `DECIDED:` |
| `label` | `use-board.py label <n> <name> [--remove]` |

## Git

The board is the commit `refs/teamwork-blackboard` names in the current folder's repository, one ref per repository: each issue is `<folder>/<n>/`, `<n>/` at the repository root, with `issue.json`, `body.md` and `comments/<k>.json`, each comment as [board-record-schema.json](../../assets/board-record-schema.json) says and an older one a `comments/<k>.md` of text alone, one commit per write, shared by every worktree of the project. A write outside a repository refuses.

- **Scope**: an issue lives at `<folder>/<n>/` of the ref's tree, `<folder>` a path from the repository root such as `teamwork`, and at `<n>/` when its project is the root. No setting names a project's folder. A project reads its folder and below, the root project only the root's own issues. Issue numbers are unique across the repository, so `read <n>` needs no folder. `file --scope <folder>` files into a folder, refused when the repository has no such folder, and with no `--scope` a manager files into its own project's folder, any other session into the root. An issue's url is `git+file://<git common dir>/refs/teamwork-blackboard/<folder>/<n>`.
- **History**: `git log --stat refs/teamwork-blackboard` shows every write; `git show refs/teamwork-blackboard:<folder>/<n>/body.md` reads one file.
- **Stale lock**: a write that finds `.git/refs/teamwork-blackboard.lock` older than 10 s refuses, naming it; remove that file once no board write runs.
- **Local only**: a plain clone, fetch or push leaves `refs/teamwork-blackboard` behind, so the board stays on this machine unless copied by name. `git push --mirror` skips it and deletes it from a remote that holds it, and a push by its own name fails with `funny refname`, since the receiving repository refuses a ref directly under `refs/`. Copy it out by `git push <remote> refs/teamwork-blackboard:refs/boards/teamwork` and in by `git fetch <remote> refs/boards/teamwork:refs/teamwork-blackboard`; `git clone --mirror` and `git fetch <url> refs/teamwork-blackboard:refs/teamwork-blackboard` carry it as it is. Checked on git 2.56.0 and 2.50.1 by `fixtures/replay-board-travel.py`.
- **Never GitHub**: team work (a task, finding, hand-over, question or answer) is written only by the calls above, never by `gh issue` or a `gh api` write, which `hooks/route-event.py` refuses from a manager, worker or sentinel; the owner's own GitHub issue runs by their `! <command>`.
- **Trusted**: every record, since only local users write the ref.
- **Default branch**: the landing adapter's, not the board's.
