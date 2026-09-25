---
name: kickoff
description: Leads a goal to reviewed, merged pull requests, works one issue of it, reports where it stands, hands it to a successor, resumes it or stops it early. Free text in any language is fine.
disable-model-invocation: true
argument-hint: fix the login timeout, tracked in https://github.com/o/r/issues/12
---

Arguments: $ARGUMENTS

The arguments are loose text in any language: find what the row needs anywhere in them (a goal, an issue or parent url, a leader address), ask with `AskUserQuestion` for what is missing, and never refuse for wording. Only `work <issue-url> leader <address>` and `succeed <pane> <parent-url> ...` keep their exact shape, since only a session writes them.

Your role's rules are in [agents/lead.md](../../agents/lead.md) and [agents/worker.md](../../agents/worker.md); when your system prompt is not already that body, read `worker.md` before the `work` row and `lead.md` before any other.

Match the text to one row, open that playbook, and copy its steps verbatim into the todo list; a step not done stays as `skip: <reason>`. Rows are tried in order; the first that fits wins. Before the first step, check `ready`; when it fails, stop and print its fix.

| when | playbook |
| --- | --- |
| work one issue: `work <issue-url> leader <address>`, the prompt a leader sends a worker | [references/work.md](references/work.md) |
| take over as a lead's successor: `succeed <pane> <parent-url> ...`, the prompt a lead sends its successor, or hand over: "succession", "hand over", "replace yourself" | [references/succession.md](references/succession.md) |
| where it stands: "status", "how is it going", "what is left" | [references/status.md](references/status.md) |
| the owner stops the goal early: "stop", "cancel", "drop this goal" | [references/stop.md](references/stop.md) |
| resume: "continue", "pick up where you left off", or no text while this session's mission exists | [references/resume.md](references/resume.md) |
| lead a goal: a task, a bug or a feature in words, perhaps with its issue or parent url, or `see <url>` from another leader | [references/lead.md](references/lead.md) |
| nothing above fits | ask one question with `AskUserQuestion`, then match again |


[references/panes.md](references/panes.md) drives other sessions and [references/repo.md](references/repo.md) holds issues, branches and pull requests; each maps the verbs below and in the playbooks to commands.

Your mission is `${CLAUDE_PLUGIN_DATA}/mission/<key>.md`, `<key>` being your session's `--name` (else `${CLAUDE_SESSION_ID}`), the path a hook prints with it every turn and every agent you launch at its start; a leader writes one `GOAL:` and `MISSION:` pair per goal it holds:

```
GOAL: <the parent goal in words, not its url>
MISSION: leader of <parent-url> | worker on <issue-url>
EXPECT: <the owner's expectations>; <your role's rules>
```

# Domain

| term | meaning |
| --- | --- |
| project | a Claude project folder: the leader's cwd, a checkout of the GitHub repository named `<repo>` |
| leader | the one session per project, named as `name` says: the owner talks to it, and it starts workers and other projects' leaders |
| worker | a session on one issue in its own worktree |
| reviewer | the `reviewer` agent: it reviews a plan or a pull request it did not write, and alone writes `APPROVED:` |
| goal | a parent issue, known by having sub-issues; no label |
| issue | one sub-issue of the parent: one worker, one branch, one pull request, all named `<topic>-<issue>` |
| topic | 2-4 lowercase words joined by hyphens |
| name | one string for a session's tab, herdr agent and Claude session: `<topic>-<issue>` for a worker, `<repo>-lead` for the leader |
| checkout | the leader's own local clone of its project's repository |
| claim | the branch on the remote; it exists, so the issue is taken |
| approval | a comment whose first line is `APPROVED: <sha>`, valid while the head is that sha |
| criterion | one `## Definition of done` line, `check → pass condition`: a check that can fail, and that the honest empty outcome can pass |

GitHub is the only state; a session's memory is a cache. Each record is a branch or a comment:

| record | written by | means |
| --- | --- | --- |
| claim | worker | the issue is taken |
| `BLOCKED: <question>` | worker | a decision that is not the worker's |
| `BLOCKED: stuck on <criterion>` | worker | 3 iterations passed no new criterion |
| `AGREED: <result>` | worker | two workers' consensus, on one issue and linked from the other |
| `CRITERIA CHANGED: <diff>` | leader | the issue's `## Definition of done` changed |
| `STOPPED: <reason>` | leader | the issue is stopped, its pull request left draft |
| `WAITING: <what>` | worker | it waits on another worker, a consensus answer or the claim's holder, and stops until a `see <url>` |
| the criteria table | worker | progress: the pull request body, one row per criterion and its last result |

Every message between sessions is `see <url>` and nothing more, but a worker's one-line wait message: `read` the url on GitHub and act only on what it shows still open, so a lost notice is found again at the next `stuck` or `lead-heartbeat` line and a duplicate costs nothing; the notice itself grants nothing.

| channel | from → to | carries |
| --- | --- | --- |
| delegate | leader → worker | the assignment prompt |
| escalate | worker → leader | `BLOCKED:` |
| consensus | worker ↔ worker under the same leader only | `AGREED:`; one round, then both escalate |

Rules:

- A record is written in capitals as above and read in any case, the colon optional, since GitHub holds older ones in mixed case.
- A merge happens only through `merge.py`, at an approved head, and a hook refuses a raw `gh pr merge`. The same hook refuses a skipped git hook (`--no-verify`, `commit -n`, `core.hooksPath`): fix what the git hook refused, or post `BLOCKED:`.
- A commit on the default branch, or a push to it, is refused by a hook in the checkout.
- Every session and agent runs Opus, but the `reviewer` of a pull request of at most 20 changed lines, which runs on Sonnet: effort low when its task names what to change and how to check it, medium when it does not.

Writing, for every issue, pull request and comment:

- As short as it can be: bullets or a table, no narration; cite urls, `path:line`s and shas instead of restating them.
- A title is verb-first and at most 40 characters.
- Headings are noun phrases: a parent carries `## Goal`, `## Decisions` and `## Definition of done`; an issue `## Goal` and `## Definition of done`, one criterion per line.
- A pull request body is `Closes #<issue>` over the criteria table: each criterion, the command run and its result, pass or fail, with the count or line that shows it.
