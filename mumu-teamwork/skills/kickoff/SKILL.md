---
name: kickoff
description: Use on the prompt `worker-start.py` or `lead-start.py` sends a new session - work a task, survey a backlog, lead a task handed over, succeed a lead, or resume.
disable-model-invocation: true
argument-hint: work https://github.com/o/r/issues/13 lead r-lead
---

Arguments: $ARGUMENTS

Match the arguments to one row by its exact shape, open that playbook, and copy its steps verbatim into the todo list; a step not done stays, marked skipped with its reason. Before the first step, check `ready`; when it fails, stop and print its fix. When your system prompt is not already your role's body, read `${CLAUDE_PLUGIN_ROOT}/agents/worker.md` before a `work` or `survey` row and `${CLAUDE_PLUGIN_ROOT}/agents/lead.md` before any other.

| when | playbook |
| --- | --- |
| work one task: `work <task-url> lead <address>` | [references/worker-playbook.md](references/worker-playbook.md) |
| survey a backlog: `survey <backlog-url> lead <address>` | [references/worker-playbook.md](references/worker-playbook.md)'s Survey |
| lead a task handed over: `see <task-url>` | [references/lead-playbook.md](references/lead-playbook.md) |
| take over as a lead's successor: `succeed <pane>` | [references/lead-playbook.md](references/lead-playbook.md)'s Succession |
| resume: no text | [references/lead-playbook.md](references/lead-playbook.md)'s Succession |
| any other text | none: reply that plain words go to the project's lead in its tab, or from any session through `/mumu-teamwork:handoff`, and stop |

# Domain

Use these terms as defined here, and define none elsewhere; Verbs maps each verb in backticks to its command.

| term | meaning |
| --- | --- |
| project | a GitHub repository `<repo>` and its lead |
| checkout | the lead's clone of its project's repository, its cwd |
| lead | the one session per project, or per plugin folder in a repository with `scope:` labels: the owner talks to it, and it holds the project's root tasks and starts workers and other projects' leads |
| worker | a session on one task, or one share of it, in its own worktree |
| judge | the `judge` agent: it judges a plan, a pull request, a report comment or a survey it did not write |
| verdict | the judge's comment: `APPROVED:` or `FINDINGS:` |
| root task | a task with no parent: its lead holds it; another project's work is a root task in that project's repository |
| task | an issue without the `backlog` label, labelled `effort:<effort>`: one change, owned by its worker, ending in one pull request closed as completed by its merge, or, when its `## Definition of done` names a report comment, in that comment, closed as completed by its worker at the report's `APPROVED:` |
| share | a row of a split task's `## Shares` table, share \| DoD \| after \| with: its topic, the ids of the criteria it checks (`D1:`), the shares it waits on, and what it shares with which; each share has its own worker, worktree, branch `<share>-<n>-<k>` and pull request; a task with no `## Shares` is one share |
| backlog | an issue labelled `backlog`: the owner's words kept for later, owned by no one and worked by no worker but a survey worker; its body is the first words as said and one `## Survey` section below them; later words go on it as comments; once its `backlog` label is removed, its body is replaced by the contract and it starts |
| body | an issue's current contract, only `## Goal`, `## Definition of done` and, split, `## Shares`, edited in place; a split task's body, labels and close are its lead's alone |
| record | a comment opening with a keyword below; any other comment is a plain reference |
| topic | 2-4 lowercase words joined by hyphens |
| attempt | 1 for a task's first worker and one more on each reopen |
| name | one string for a session's tab, herdr agent and Claude session, and a worker's worktree and branch: `<topic>-<n>-<k>` for a worker on task n, attempt k; `<repo>-lead` for the lead, or `<folder>-lead` for a folder's, `<repo>` the repository's name lowercased, each run of other than letters, digits, hyphens and underscores one hyphen, cut to 22 characters |
| criterion | one `## Definition of done` line, its kind, then a check → its pass condition: a check that can fail, and that the honest empty outcome can pass |
| kind | a criterion's first token: `[exists]`, a file or line is present or absent; `[test]`, a test passes; `[quality]`, a rubric score; one comparing head with main names its sample, at least 3 outputs per prompt per side, the paired mean per lens and the margin head's mean must beat main's by |
| playbook | a file of `references/`: a role's changing rules and steps |

Keep all state on GitHub; a session's memory is a cache. The records:

| keyword | written by | means |
| --- | --- | --- |
| `BLOCKED:` | worker | `BLOCKED: <question>`, a decision that is not the worker's, or `BLOCKED: stuck on <criterion>`; a share's worker opens it `BLOCKED: <share>:` |
| `DECIDED:` | lead | `DECIDED: <answer>`, a decision and its reason, posted with `decide` |
| `APPROVED:` | judge | `APPROVED: <sha>`: the pull request may merge while its head is that sha or a merge of the default branch into it that leaves its own diff byte-identical; `APPROVED: <comment-url>`: the report may close; `APPROVED:` alone: the plan or survey may go on |
| `FINDINGS:` | judge | one line per criterion missed |

Talk to another session through one of two channels, never mixed:

| channel | from → to | instrument | carries |
| --- | --- | --- | --- |
| directing | a lead → its worker or another project's lead; a worker → its lead | `prompt` | `see <url>` and nothing more |
| agreeing | a lead ↔ another live lead of the same repository; a share's worker ↔ a sibling share's worker of the same task | `SendMessage` to a name `ListAgents` shows | a proposal opening `Proposal from <name>:` and ending `Reply OK or an objection.`, and its answer, `OK` or an objection with its reason |

On `see <url>`, `read` the url and act only on what it shows still open. Send a proposal before the change it names and act after every answer; on an objection, revise and ask again; past two objections, or with no answer after one resend, escalate as the playbook says. Record only a proposal's outcome, never the exchange.

Rules:

- Write a keyword in capitals as above; read it in any case, the colon optional.
- Merge only with `merge`; fix what a git hook refuses, never skip it, or post `BLOCKED:`.
- Commit and push only on a branch other than the default; a merge squashes and deletes its head branch.
- Run every session and agent on Opus, but a pull request's `judge` on the model `judge-model.py origin/<default> HEAD` prints.
- Launch the `judge` on a url, and after fixing its `FINDINGS:` resume that judge with `see <url>`, launching a new one only when it cannot be resumed and the url shows no verdict at the head.

Writing, for every issue, pull request and comment:

- As short as it can be: bullets or a table, no narration; cite urls, `path:line`s and shas instead of restating them.
- A title is verb-first and at most 40 characters.
- Headings are noun phrases: a body carries `## Goal` and `## Definition of done`, one criterion per line.
- A pull request body is `Closes #<task>`, or a share's `Part of #<task>`, over the criteria table: each criterion, the command run and its result, pass or fail, with the count or line that shows it, and an `on main` column, filled for a `[test]` row with the new test's failing line run against the default branch.
- A report comment is the findings over the same criteria table.

# Verbs

Write a body, a comment or a decision with a file tool to `<path>` first, never as a heredoc. File a task in its lead's repository, and add a worker's worktree in its lead's checkout only. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, and `<hooks>` is `git -C <checkout> rev-parse --path-format=absolute --git-path hooks`.

Run `start`, `start-lead`, `close`, `merge` and `clean`'s git commands each as the literal command written, one Bash call of its own by its bare name, with no path, interpreter, `cd`, `&&`, `;`, pipe, loop, redirect or variable. Run the same git step in a checkout other than the cwd as `git -C <literal path> <step>`, its one git option.

## Panes: herdr

Name the target pane in every command.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; the fix is to run inside herdr, and `herdr integration install claude` |
| your address | your bare name, never `<name>@<pane>` |
| `live` | `herdr agent list`: each agent's pane, tab and `agent_status` |
| `start` | `worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--lead <your address>] [--owner-effort] [--survey]`: starts the worker `<topic>-<n>-<k>` at the next attempt, or the newest with `--continue`, in its own worktree and tab, prompted kickoff's `work`, or with `--survey` a backlog's survey worker prompted `survey`; it refuses a task closed, labelled `backlog` without `--survey`, not labelled `backlog` with it, blocked, at another effort than its label, or a share before its `after` shares merged |
| `rename` | give this session a name: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"` |
| `prompt` | `herdr agent prompt <name> "<text>"`, by name; read the pane before and after, and resend when no turn carries the text; failing twice, tell the owner |
| `start-lead` | `lead-start.py <checkout> [<task-url>] [--folder <folder>] [-- <claude flags>]`, or `--succeed <pane>` for the task and folder, or `--replace` to close the calling session once its turn ends, at the checkout's root: starts `<repo>-lead`, or `<folder>-lead` with `--folder`, in a new tab, refusing when one is live, and prompts its kickoff; leave a start-up dialog in its tab to the owner |
| `broadcast` | `prompt` each lead in `live` but you `see <url>`, one `herdr agent prompt <literal-name> "see <url>"` Bash call per agent, no loop and no variable; after the sends, read `live` again and `prompt` each lead name new or reappeared |
| `close` | `session-close.py <name>`: exits the session, answering its exit dialogs, and closes each tab labelled `<name>`, the session live or gone |

## Repo: GitHub and git

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state,parent`, or `gh pr view <url> --json title,body,comments,headRefOid` |
| `file` | `gh label create <label> -R <repo> --force` for each label, then `gh issue create -R <repo> --title "<title>" --label <label>... --body-file <path>`; a task's effort is low when it names what to change and how to check it, else medium, unless the owner named another |
| `order` | make a task wait on another until it closes: `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>`, `<id>` the blocker's `gh api repos/<owner>/<repo>/issues/<m> -q .id`, in this repository or another |
| `comment` | `gh issue comment <url> --body-file <path>` |
| `decide` | `decision-post.py <url> [--criteria <file>] < <path>`: posts `DECIDED: <decision>`, the text of `<path>`, and with `--criteria` first replaces the body's `## Definition of done` by the file's lines |
| `resolve` | `gh issue close <url> --reason completed --comment "<summary>"`, refused for a split task while a share has no merged pull request `<share>-<n>-<k>` |
| `stop` | close an issue as not planned: `gh issue close <url> --reason "not planned" --comment "<reason>"`, then `gh pr ready --undo <pr-url>` for its open pull request |
| `claim` | take an attempt by its branch on the remote: `git fetch origin && ! git ls-remote --exit-code origin refs/heads/<branch> && git push -u origin <branch>`, `<branch>` the worktree's own, named after it; a branch found is yours only when this checkout is on it |
| `pr` | `gh pr create --base <default> --head <branch> --title "<title>" --body-file <path>`; later `gh pr edit <pr> --body-file <path>` |
| `merge` | `pr-merge.py <pr-url>`: squash-merges pinned to the head only when the newest verdict opens `APPROVED: <head>`, or `APPROVED: <A>` carried to it: every commit on `git rev-list --first-parent A..head` a merge of `origin/<default>`, and `git patch-id --verbatim` of the diff from the merge base the same at A and head |
| `clean` | from the checkout's root, one literal Bash call per command per worker, with no `git -C`, `cd` prefix, loop, `$(...)` or variable: `git worktree remove .claude/worktrees/<name>`, `git branch -D <name>` and, while `git ls-remote --exit-code origin refs/heads/<name>` finds it, `git push origin --delete <name>`; then `git pull --ff-only`, and remove the hook when `cmp -s` finds it equal to `default-branch-guard.sh` as `rm <hooks>/pre-commit`, `<hooks>` written out as its literal path |

## Traps

- `pr` and `merge`: after an error such as `GraphQL: Something went wrong`, `read` the state before retrying; just after a push, read the head with `git ls-remote origin refs/heads/<branch>`, not `headRefOid`.
- CI: wait in the foreground with `gh run watch <id> --exit-status`, never on `gh pr checks`; a conflicting pull request gets no run.
