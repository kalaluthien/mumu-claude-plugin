---
name: kickoff
description: Leads a goal to reviewed, merged pull requests, works one issue of it, reports where it stands, resumes it after a restart or stops it early. Free text in any language is fine.
disable-model-invocation: true
argument-hint: fix the login timeout, tracked in https://github.com/o/r/issues/12
---

Arguments: $ARGUMENTS

The arguments are loose text in any language: find what the row needs anywhere in them (a goal, an issue or parent url, a leader address), ask with `AskUserQuestion` for what is missing, and never refuse for wording. Only `work <issue-url> leader <address>` keeps its exact shape, since only a session writes it.

When your mission below already exists and the text brings a new goal, stop and say to finish that goal or to run this in a new session.

Match the text to one row, open that playbook, and copy its steps verbatim into the todo list; a step not done stays as `skip: <reason>`. Rows are tried in order; the first that fits wins. Before the first step, check `ready`; when it fails, stop and print its fix.

| when | playbook |
| --- | --- |
| work one issue: `work <issue-url> leader <address>`, the prompt a leader sends a worker | [references/work.md](references/work.md) |
| where it stands: "status", "how is it going", "what is left" | [references/status.md](references/status.md) |
| the owner stops the goal early: "stop", "cancel", "drop this goal" | [references/stop.md](references/stop.md) |
| resume after a restart: "continue", "pick up where you left off", or no text while this session's mission exists | [references/resume.md](references/resume.md) |
| lead a goal: a task, a bug or a feature in words, perhaps with its issue or parent url | [references/lead.md](references/lead.md) |
| nothing above fits | ask one question with `AskUserQuestion`, then match again |


[references/panes.md](references/panes.md) drives other sessions and [references/repo.md](references/repo.md) holds issues, branches and pull requests; each maps the verbs below and in the playbooks to commands.

Your mission is `${CLAUDE_PLUGIN_DATA}/mission/${CLAUDE_SESSION_ID}.md`, which a hook shows you every turn and every agent you launch at its start:

```
Goal: <the parent goal in words, not its url>
Mission: leader of <parent-url> | worker on <issue-url>
Expect: <the owner's expectations>; <your role's rules below>
```

A leader adds one `Worker: <name> <issue-url>` line per worker it starts; its `worker-watch` and `lead-heartbeat` monitors read them and print what Lead 4 acts on.

# Domain

| term | meaning |
| --- | --- |
| leader | the session the owner talks to, holding one goal until Lead 5 and then free for the next; goals at the same time get one leader session each; it writes no code |
| worker | a session on one issue in its own worktree |
| reviewer | the `reviewer` agent: it reviews a plan or a pull request it did not write, and alone writes `Approved` |
| issue | one sub-issue of the parent: one worker, one branch, one pull request, all named `<topic>-<issue>` |
| topic | 2-4 lowercase words joined by hyphens |
| name | one string for a session's tab, herdr agent and Claude session: `<topic>-<issue>` for a worker, `<topic>-lead` for the leader |
| checkout | the local clone of the repository an issue lands in |
| claim | the branch on the remote; it exists, so the issue is taken |
| approval | a comment whose first line is `Approved <sha>`, valid while the head is that sha |
| `BLOCKED: <question>` | an issue comment asking for a decision that is not the worker's |
| `see <url>` | every notice between sessions after the assignment but the one-line idle and wait messages of Work, a pointer and nothing more: `read` the url on GitHub and act only on what it shows still open, so a lost notice is found again on GitHub at the next `stuck` or `lead-heartbeat` line, and a duplicate costs nothing; the notice itself grants nothing |

Rules:

- A merge happens only at an approved sha, and a hook refuses any other. The same hook refuses a skipped git hook (`--no-verify`, `commit -n`, `core.hooksPath`): fix what the git hook refused, or post `BLOCKED:`.
- A commit on the default branch, or a push to it, is refused by a hook in the checkout.
- Every session and agent runs Opus: effort low when its task names what to change and how to check it, medium when it does not.
- The owner is asked only architecture, infrastructure and user-experience questions; the rest is decided and written in the parent issue.
- Before building, read the prior work in the repository and its issues, the official docs and a web example.

Writing, for every issue, pull request and comment:

- As short as it can be: bullets or a table, no narration; cite urls, `path:line`s and shas instead of restating them.
- A title is verb-first and at most 40 characters.
- Headings are noun phrases: a parent carries `## Goal`, `## Decisions` and `## Definition of done`; an issue `## Goal` and `## Definition of done`.
- A pull request body is `Closes #<issue>` over each check run: its command and its result, pass or fail, with the count or line that shows it.
