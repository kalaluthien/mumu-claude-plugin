---
name: kickoff
description: Starts a session on its mumu-team role from the prompt a script sends it - work a task, lead a handed-over goal, succeed a lead, or resume.
disable-model-invocation: true
argument-hint: work https://github.com/o/r/issues/13 leader r-lead
---

Arguments: $ARGUMENTS

Only `worker-start.py` and `lead-start.py` build these arguments, and send them through herdr as the session's first prompt: match their exact shape. Any other text was typed by hand.

Your role's rules are in [agents/lead.md](../../agents/lead.md) and [agents/worker.md](../../agents/worker.md); when your system prompt is not already that body, read the worker's before the `work` row and the lead's before any other.

Match the text to one row, open that playbook, and copy its steps verbatim into the todo list; a step not done stays, marked skipped with its reason. Before the first step, check `ready`; when it fails, stop and print its fix.

| when | playbook |
| --- | --- |
| work one task: `work <task-url> leader <address>`, from `worker-start.py --leader` | [references/work-task.md](references/work-task.md) |
| lead a goal handed over: `see <goal-url>`, from `lead-start.py <checkout> <goal-url>` | [references/lead-goal.md](references/lead-goal.md) |
| take over as a lead's successor: `succeed <pane>`, from `lead-start.py --succeed` | [references/lead-goal.md](references/lead-goal.md)'s Succession |
| resume: no text, from `lead-start.py <checkout>` | [references/lead-goal.md](references/lead-goal.md)'s Succession |
| any other text | none: reply that plain words go to the project's lead in its tab, or from any session through `/mumu-team:handoff`, and stop |


Verbs, at the end, maps the verbs below and in the playbooks to commands.

# Domain

The only place these terms are defined; every other file uses them as written here.

| term | meaning |
| --- | --- |
| project | a Claude project folder: the leader's cwd, a checkout of the GitHub repository named `<repo>` |
| leader | the one session per project, or per plugin folder in a repository with `scope:` labels, named as `name` says: the owner talks to it, and it holds the project's root goals and root tasks and starts workers and other projects' leaders |
| worker | a session on one task in its own worktree |
| reviewer | the `reviewer` agent: it reviews a plan, a pull request or a report comment it did not write, and alone writes `APPROVED:` |
| goal | an issue labelled `kind:goal`: an outcome the owner wants, filed only when it holds two or more tasks, owned by its project's leader, split into goals or tasks at any depth, related or not; its criteria state outcomes, never that a task below merged, and "the owner says it is done" is one; closed as completed when all it holds is done and its criteria pass |
| root goal, root task | a goal or task with no parent: the leader holds it; another project's work is a root goal or root task in that project's repository; a chore is a root task, `effort:low` |
| task | an issue labelled `kind:task` and `effort:<effort>`, under a goal or a root task itself: one change, one worker, never split, owned by its worker; it ends in one pull request, closed as completed by its merge, or, when its `## Definition of done` names a report comment, in that comment on the task, closed as completed by its worker at the report's `APPROVED:` |
| backlog | an issue labelled `kind:backlog`: the owner's words kept for later, owned by no one and never worked; its body is the first words as said, and later words go on it as comments; relabelled `kind:goal` or `kind:task`, its body is replaced by the contract and it starts |
| kind | exactly one of the labels `kind:goal`, `kind:task`, `kind:backlog`. A closed issue of the same kind as new work is reopened, never filed again |
| body | an issue's current contract, only `## Goal` and `## Definition of done`, edited in place |
| comment | history: a record opening with its keyword, or a plain reference comment |
| topic | 2-4 lowercase words joined by hyphens |
| attempt | 1 for a task's first worker and one more on each reopen |
| name | one string for a session's tab, herdr agent and Claude session, and a worker's worktree and branch: `<topic>-<n>-<k>` for a worker on task n, attempt k; `<repo>-lead` for the leader, or `<folder>-lead` for a folder's, `<repo>` the repository's name lowercased, each run of other than letters, digits, hyphens and underscores one hyphen, cut to 22 characters, as herdr allows |
| checkout | the leader's own local clone of its project's repository |
| claim | the branch on the remote; it exists, so the attempt is taken |
| order | a task or goal waits on another by GitHub's blocked-by, and starts once each blocker is closed |
| approval | a comment whose first line is `APPROVED: <sha>`, valid while the head is that sha, or `APPROVED: <comment-url>` for a report |
| criterion | one `## Definition of done` line, a check → its pass condition: a check that can fail, and that the honest empty outcome can pass |
| stop | an issue closed as not planned, its pull request left draft |

GitHub is the only state; a session's memory is a cache. A record is a comment opening with one of four keywords:

| keyword | written by | means |
| --- | --- | --- |
| `BLOCKED:` | worker | `BLOCKED: <question>`, a decision that is not the worker's, or `BLOCKED: stuck on <criterion>`, 3 iterations passed no new criterion |
| `DECIDED:` | leader | `DECIDED: <answer>` through `decide.py`, which also edits the body's criteria when they change |
| `APPROVED:` | reviewer | the plan, the pull request at the head sha it names, or the report comment it names, may go on |
| `FINDINGS:` | reviewer | one line per defect: where, the defect, the fix |

The criteria table in the pull request body, or in a report comment, is a worker's progress: one row per criterion and its last result.

Sessions talk through two channels, never mixed:

| channel | from → to | instrument | carries |
| --- | --- | --- | --- |
| directing | a leader → its worker or another project's leader; a worker → its leader | `herdr agent prompt`, as Verbs maps it | `see <url>` and nothing more, never a proposal |
| agreeing | a lead ↔ another live lead of the same repository | `SendMessage` to a name `ListAgents` shows, as [lead-goal.md](references/lead-goal.md)'s Folder leads says | a proposal and its answer, never an order |

A directing notice grants nothing: `read` its url on GitHub and act only on what it shows still open, so a lost notice is found again at the next `team-watch` line and a duplicate costs nothing. Its url points at:

| notice | from → to | url shows |
| --- | --- | --- |
| delegate | leader → worker | the assignment |
| escalate | worker → leader | `BLOCKED:` |
| answer | leader → worker | `DECIDED:` |

Rules:

- A keyword is written in capitals as above and read in any case, the colon optional.
- A merge happens only through `merge.py`, at an approved head, and a hook refuses a raw `gh pr merge`. The same hook refuses a skipped git hook: fix what the git hook refused, or post `BLOCKED:`.
- A commit on the default branch, or a push to it, is refused by a hook in the checkout.
- Every session and agent runs Opus, but the `reviewer` of a pull request of at most 20 changed lines, which runs on Sonnet: effort low when its task names what to change and how to check it, medium when it does not.

Writing, for every issue, pull request and comment:

- As short as it can be: bullets or a table, no narration; cite urls, `path:line`s and shas instead of restating them.
- A title is verb-first and at most 40 characters.
- Headings are noun phrases: a body carries `## Goal` and `## Definition of done`, one criterion per line; decisions and their reasons are `DECIDED:` comments.
- A pull request body is `Closes #<task>` over the criteria table: each criterion, the command run and its result, pass or fail, with the count or line that shows it.

# Verbs

A goal and its tasks live in its leader's repository, and a worker's worktree in its leader's own checkout only. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, and `<hooks>` is `git -C <checkout> rev-parse --path-format=absolute --git-path hooks`.

## Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; the fix is to run inside herdr, and `herdr integration install claude` |
| your address | your bare name, which `herdr agent get` resolves; `<name>@<pane>` is not found |
| `live` | `herdr agent list`, whose JSON gives each agent's pane, tab and `agent_status` |
| `start` | `worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <your address>] [--owner-effort]`: starts the worker `<topic>-<n>-<k>` at the next attempt, or the newest with `--continue`, in its own worktree and tab, prompted kickoff's `work` |
| `name` | this session's three names: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`, which applies when the turn ends |
| `prompt` | `herdr agent prompt <name> "<text>"`, by name, since a remembered pane id can be stale; success prints before delivery and a busy pane or open dialog can swallow the text, so read the pane before and after and resend when no turn carries it; failing twice, tell the owner |
| `start-lead` | `lead-start.py <checkout> [<goal-url> \| --succeed <pane>] [-- <claude flags>]`, at the checkout's root: starts `<repo>-lead` in a new tab, refusing when one is live, and prompts its kickoff; a start-up dialog in its tab is the owner's to answer there |
| `broadcast` | `prompt` each lead in `live` but you `see <url>`, one `herdr agent prompt <literal-name> "see <url>"` Bash call per agent, no loop and no variable, so the allow rule matches it |
| `close` | `worker-close.py <name>`: exits the session, answering its exit dialogs, and closes each tab labelled `<name>`, the session live or gone |

## Repo: GitHub and git

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state,parent`, or `gh pr view <url> --json title,body,comments,headRefOid`; what a goal holds is its sub-issues, `gh api repos/<repo>/issues/<n>/sub_issues`, each read the same way down to the tasks |
| `file` | `gh label create <label> -R <repo> --force` for each label, then `gh issue create -R <repo> --title "<title>" --label <label>... --body-file -`, with `--parent <goal-url>` unless it is a root goal or root task; a task's effort is low or medium unless the owner named another |
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
