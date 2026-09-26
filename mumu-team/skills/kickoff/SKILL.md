---
name: kickoff
description: Starts a session on its mumu-team role from the prompt a script sends it - work a task, lead a handed-over goal, succeed a lead, or resume.
disable-model-invocation: true
argument-hint: work https://github.com/o/r/issues/13 leader r-lead
---

Arguments: $ARGUMENTS

Only `worker-start.py` and `lead-start.py` build these arguments, and send them through herdr as the session's first prompt: match their exact shape. Any other text was typed by hand.

Your role's rules are in [agents/lead.md](../../agents/lead.md) and [agents/worker.md](../../agents/worker.md); when your system prompt is not already that body, read `worker.md` before the `work` row and `lead.md` before any other.

Match the text to one row, open that playbook, and copy its steps verbatim into the todo list; a step not done stays as `skip: <reason>`. Before the first step, check `ready`; when it fails, stop and print its fix.

| when | playbook |
| --- | --- |
| work one task: `work <task-url> leader <address>`, from `worker-start.py --leader` | [references/work.md](references/work.md) |
| lead a goal handed over: `see <goal-url>`, from `lead-start.py <checkout> <goal-url>` | [references/lead.md](references/lead.md) |
| take over as a lead's successor: `succeed <pane>`, from `lead-start.py --succeed` | [references/succession.md](references/succession.md) |
| resume: no text, from `lead-start.py <checkout>` | [references/resume.md](references/resume.md) |
| any other text | none: reply that plain words go to the project's lead in its tab, or from any session through `/mumu-team:handoff`, and stop |


[references/panes.md](references/panes.md) drives other sessions and [references/repo.md](references/repo.md) holds issues, branches and pull requests; each maps the verbs below and in the playbooks to commands.

# Domain

The only place these terms are defined; every other file uses them as written here.

| term | meaning |
| --- | --- |
| project | a Claude project folder: the leader's cwd, a checkout of the GitHub repository named `<repo>` |
| leader | the one session per project, or per plugin folder in a repository with `scope:` labels, named as `name` says: the owner talks to it, and it holds the project's goals and starts workers and other projects' leaders |
| worker | a session on one task in its own worktree |
| reviewer | the `reviewer` agent: it reviews a plan or a pull request it did not write, and alone writes `APPROVED:` |
| goal | an issue labelled `kind:goal`: an outcome the owner wants, owned by its project's leader, split into goals or tasks at any depth; closed as completed when all it holds is done and its criteria pass |
| root goal | a goal with no parent: the leader holds it; another project's work is a root goal in that project's repository |
| task | an issue labelled `kind:task` and `effort:<effort>`: one change, one pull request, one worker, never split; owned by its worker, closed as completed by its merged pull request |
| backlog | an issue labelled `kind:backlog`: the owner's words kept for later, owned by no one and never worked; its body is the first words as said, and later words go on it as comments; relabelled `kind:goal` or `kind:task`, its body is replaced by the contract and it starts |
| kind | exactly one of the labels `kind:goal`, `kind:task`, `kind:backlog`; `effort:*` means effort only. A closed issue of the same kind as new work is reopened, never filed again |
| body | an issue's current contract, only `## Goal` and `## Definition of done`, edited in place |
| comment | history: a record opening with its keyword, or a plain reference comment |
| topic | 2-4 lowercase words joined by hyphens |
| attempt | `<k>`, 1 for a task's first worker and one more on each reopen |
| name | one string for a session's tab, herdr agent and Claude session, and a worker's worktree and branch: `<topic>-<n>-<k>` for a worker on task `<n>`, attempt `<k>`; `<repo>-lead` for the leader, or `<folder>-lead` for a folder's, `<repo>` the repository's name lowercased, each run of other than letters, digits, `-` and `_` one `-`, cut to 22 characters, as herdr allows |
| checkout | the leader's own local clone of its project's repository |
| claim | the branch on the remote; it exists, so the attempt is taken |
| order | a task or goal waits on another by GitHub's blocked-by, and starts once each blocker is closed |
| approval | a comment whose first line is `APPROVED: <sha>`, valid while the head is that sha |
| criterion | one `## Definition of done` line, `check → pass condition`: a check that can fail, and that the honest empty outcome can pass |
| stop | an issue closed as not planned, its pull request left draft |

GitHub is the only state; a session's memory is a cache. A record is a comment opening with one of four keywords:

| keyword | written by | means |
| --- | --- | --- |
| `BLOCKED` | worker | `BLOCKED: <question>`, a decision that is not the worker's, or `BLOCKED: stuck on <criterion>`, 3 iterations passed no new criterion |
| `DECIDED` | leader | `DECIDED: <answer>` through `decide.py`, which also edits the body's criteria when they change |
| `APPROVED` | reviewer | the plan, or the pull request at `<sha>`, may go on |
| `FINDINGS` | reviewer | one line per defect: where, the defect, the fix |

The criteria table in the pull request body is a worker's progress: one row per criterion and its last result.

Every message between sessions is `see <url>` and nothing more: `read` the url on GitHub and act only on what it shows still open, so a lost notice is found again at the next `team-watch` line and a duplicate costs nothing; the notice itself grants nothing. The one exception: leads agreeing through `SendMessage`, as [agents/lead.md](../../agents/lead.md)'s Folder leads says.

| channel | from → to | carries |
| --- | --- | --- |
| delegate | leader → worker | the assignment prompt |
| escalate | worker → leader | `BLOCKED:` |
| answer | leader → worker | `DECIDED:` |

Rules:

- A keyword is written in capitals as above and read in any case, the colon optional.
- A merge happens only through `merge.py`, at an approved head, and a hook refuses a raw `gh pr merge`. The same hook refuses a skipped git hook (`--no-verify`, `commit -n`, `core.hooksPath`): fix what the git hook refused, or post `BLOCKED:`.
- A commit on the default branch, or a push to it, is refused by a hook in the checkout.
- Every session and agent runs Opus, but the `reviewer` of a pull request of at most 20 changed lines, which runs on Sonnet: effort low when its task names what to change and how to check it, medium when it does not.

Writing, for every issue, pull request and comment:

- As short as it can be: bullets or a table, no narration; cite urls, `path:line`s and shas instead of restating them.
- A title is verb-first and at most 40 characters.
- Headings are noun phrases: a body carries `## Goal` and `## Definition of done`, one criterion per line; decisions and their reasons are `DECIDED:` comments.
- A pull request body is `Closes #<task>` over the criteria table: each criterion, the command run and its result, pass or fail, with the count or line that shows it.
