# Board

Each operation is one call of `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/use-board.py`, each field a named option and the script writing the keyword line itself, with each `--body` or `--text` in a file written first by the Write tool, never a bare `cat >` in a chained call, which waits on stdin until the call times out.

| operation | how |
| --- | --- |
| `read` | `use-board.py read <n> [--as worker\|judge]` |
| `comment` | `use-board.py comment <n> --blocked <question> [--text <file>]` to ask, `use-board.py comment <n> --reported <line> [--text <file>]` to inform |
| `file` | `use-board.py file --title <title> --body <file> [--label <name>] [--scope <folder>]` |
| `edit` | `use-board.py edit <n> --body <file> --reason <what changed and why> --base <sha>`, the whole new body, made from what `use-board.py read <n> --body` prints, and the `body sha` `read` printed, refused when the body has changed since; the title by `use-board.py title <n> --title <title>` |
| `resolve` | `use-board.py resolve <n> --summary <line> [--text <file>] [--not-planned]` |
| `reopen` | `use-board.py reopen <n>` |
| `decide` | `use-board.py decide <n> --decision <sentence> [--text <file>]` |
| `label` | `use-board.py label <n> --label <name> [--remove]` |

## Git

The board is the commit `refs/teamwork-blackboard` names in the repository of the current folder, or of the `--repository <folder>` a call names, one ref per repository: each task is `<folder>/<n>/`, `<n>/` at the repository root, with `task.json`, `body.md` and `comments/<k>.json`, each comment as [board-record-schema.json](../../assets/board-record-schema.json) says, one commit per write, shared by every worktree of the project. A write outside a repository refuses.

- **Scope**: `<folder>` is a path from the repository root, such as `teamwork`. No setting names a project's folder. A project reads its folder and below, the root project only the root's own tasks. Task numbers are unique across the repository, so `read <n>` needs no folder. `file --scope <folder>` files into a folder, refused when the repository has no such folder, and with no `--scope` a manager files into its own project's folder, any other session into the root. A task's url is `git+file://<git common dir>/refs/teamwork-blackboard/<folder>/<n>`.
- **Local only**: a plain clone, fetch or push leaves `refs/teamwork-blackboard` behind, so the board stays on this machine unless copied by name. `git push --mirror` skips it and deletes it from a remote that holds it, and a push by its own name fails with `funny refname`, since the receiving repository refuses a ref directly under `refs/`. Copy it out by `git push <remote> refs/teamwork-blackboard:refs/boards/teamwork` and in by `git fetch <remote> refs/boards/teamwork:refs/teamwork-blackboard`; `git clone --mirror` and `git fetch <url> refs/teamwork-blackboard:refs/teamwork-blackboard` carry it as it is.
- **Never GitHub**: team work (a task, finding, hand-over, question or answer) is written only by the calls above, never by `gh issue` or a `gh api` write, which `hooks/route-event.py` refuses from a manager, worker or sentinel; the owner's own GitHub issue runs by their `! <command>`.
- **Trusted**: every record, since only local users write the ref.
