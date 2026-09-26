# Verbs

The command each verb runs. A goal and its tasks live in its leader's repository, and a worker's worktree in its leader's own checkout only. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, and `<hooks>` is `git -C <checkout> rev-parse --path-format=absolute --git-path hooks`.

## Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; the fix is to run inside herdr, and `herdr integration install claude` |
| your address | your bare name, which `herdr agent get` resolves; `<name>@<pane>` is not found |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <your address>] [--owner-effort]`: `<effort>` is `low` or `medium` unless `--owner-effort` says the owner named another; starts the worker `<topic>-<n>-<k>` at the next attempt, or the newest with `--continue`, in its own worktree and tab, prompted kickoff's `work` |
| `name` | this session's three names: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`, which applies when the turn ends |
| `prompt` | `herdr agent prompt <name> "<text>"`, by name, since a remembered pane id can be stale; success prints before delivery and a busy pane or open dialog can swallow the text, so read the pane before and after and resend when no turn carries it; failing twice, tell the owner |
| `start-lead` | `lead-start.py <checkout> [<goal-url> \| --succeed <pane>] [-- <claude flags>]`, at the checkout's root: starts `<repo>-lead` in a new tab, refusing when one is live, and prompts its kickoff; a start-up dialog in its tab is the owner's to answer there |
| `broadcast` | `prompt` each agent in `live` whose name ends in `-lead`, but you, `see <url>`, one `herdr agent prompt <literal-name> "see <url>"` Bash call per agent, no loop and no variable, so the allow rule matches it |
| `close` | `worker-close.py <name>`: exits the session, answering its exit dialogs, and closes each tab labelled `<name>`, the session live or gone |

## Repo: GitHub and git

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state,parent`, or `gh pr view <url> --json title,body,comments,headRefOid`; what a goal holds is its sub-issues, `gh api repos/<repo>/issues/<n>/sub_issues`, each read the same way down to the tasks |
| `file` | `gh label create <label> -R <repo> --force` for each label, then `gh issue create -R <repo> --title "<title>" --label <label>... --body-file -`, with `--parent <goal-url>` unless it is a root goal or root task; a task's effort is `low` or `medium` unless the owner named another |
| `order` | `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>`, `<id>` the blocker's `gh api repos/<owner>/<repo>/issues/<m> -q .id`, in this repository or another |
| `comment` | `gh issue comment <url> --body-file -` |
| `decide` | `decide.py <url> [--criteria <file>] < <decision>`: posts `DECIDED: <decision>`, and with `--criteria` first replaces the body's `## Definition of done` by the file's lines |
| `resolve` | `gh issue close <url> --reason completed --comment "<summary>"` |
| `stop` | `gh issue close <url> --reason "not planned" --comment "<reason>"`, then `gh pr ready --undo <pr-url>` for its open pull request |
| `claim` | `git fetch origin && ! git ls-remote --exit-code origin refs/heads/<branch> && git switch -c <branch> origin/<default> && git push -u origin <branch>`, the branch named after the worktree; a branch found is yours only when this checkout is on it |
| `pr` | `gh pr create --base <default> --head <branch> --title "<title>" --body-file -`; later `gh pr edit <pr> --body-file -` |
| `merge` | `merge.py <pr-url>`: squash-merges pinned to the head only when a comment or review opens `APPROVED: <head>` |
| `clean` | for each worker `git -C <checkout> worktree remove <worktree>`, `git -C <checkout> branch -D <branch>` and `git -C <checkout> push origin --delete <branch>`; then `git -C <checkout> pull --ff-only`, and remove each hook `cmp -s` finds equal to `default-branch-guard.sh` as `rm <hooks>/pre-commit` or `rm <hooks>/pre-push`, `<hooks>` written out as its literal path, no variable, so the allow rules match it |

## Traps

- `file`: `--parent` creates the issue even when the link fails, so relink the printed url with `gh issue edit <url> --parent <goal-url>`, never create it again.
- `pr` and `merge`: an error such as `GraphQL: Something went wrong` may still have landed, so `read` the state before retrying; just after a push `headRefOid` can name the old head, which `git ls-remote origin refs/heads/<branch>` does not.
- CI: a conflicting pull request gets no run, and a job with `needs` is absent from `gh pr checks` until they finish, so wait in the foreground with `gh run watch <id> --exit-status`.
