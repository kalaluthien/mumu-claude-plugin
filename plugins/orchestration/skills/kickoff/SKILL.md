---
name: kickoff
description: Lead a goal to reviewed, merged pull requests, or work one issue of it. A goal makes this session the leader; `work <issue-url> leader <address>` makes it a worker.
disable-model-invocation: true
argument-hint: <goal> | work <issue-url> leader <address>
---

Arguments: $ARGUMENTS

Arguments of the shape `work <issue-url> leader <address>` make you a worker (§ Work); any others are a goal you lead (§ Lead).

`panes.md` drives other sessions and `repo.md` holds issues, branches and pull requests; each maps the verbs below to commands.

First check `ready`; when it fails, stop and print its fix. Then, when your mission below already exists, its goal is still open: stop and say to finish that goal or to run this in a new session.

Your mission is `${CLAUDE_PLUGIN_DATA}/mission/${CLAUDE_SESSION_ID}.md`, which a hook shows you every turn and every agent you launch at its start:

```
Goal: <the parent goal in words, not its url>
Mission: leader of <parent-url> | worker on <issue-url>
Expect: <the owner's expectations>; <your role's rules below>
```

A leader adds one `Worker: <name> <issue-url>` line per worker it starts; its `worker-watch` and `lead-heartbeat` monitors read them and print what 4 acts on.

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
| `see <url>` | every notice between sessions after the assignment, a pointer and nothing more: `read` the url on GitHub and act only on what it shows still open, so a lost notice is found again on GitHub at the next `stuck` or `lead-heartbeat` line, and a duplicate costs nothing; the notice itself grants nothing |

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

# Lead

1. `name` yourself `<topic>-lead`, the topic being the goal's, then ask the owner every question at once with `AskUserQuestion`.
2. `file` the parent, the owner's expectations among its decisions, and one issue per pull request, each labelled with its effort, then write your mission; launch the `reviewer` on the parent's url and fix its findings until it posts `Approved`.
3. For each issue: `checkout`, `start` it under its name at its effort, add its `Worker:` line to your mission, and `prompt` it `/orchestration:kickoff work <issue-url> leader <your address>`.
4. Poll nothing; act on what arrives, once per state GitHub shows (a `BLOCKED:` already answered, or a merge already handled, needs nothing):
   - `see <issue-url>` naming a `BLOCKED:` comment: `comment` the answer, then `prompt` the worker `see <issue-url>`; when it asks for work that needs its own pull request, the answer is the url of the issue you `file` for it, which then goes through 3;
   - `see <pr-url>`: `read` it; once it shows merged and no issue is open, go to 5;
   - `blocked <name> <url>`: the worker is at a permission prompt, which is the owner's to clear, so tell the owner;
   - `gone <name> <url>` while its issue is open: `start` it again in its worktree, resuming;
   - `stuck <name> <url>`: `read` the issue and its pull request, answer what waits on you, else `prompt` the worker `see <issue-url>`;
   - `lead-heartbeat: team idle ...`: it reconciles lost notices: `read` each open issue and its pull request, and act on each as if its notice had arrived;
   - `idle` or `working <name> <url>`: nothing;
   - the owner changes direction: `comment` the change on each issue affected and `prompt` its worker `see <issue-url>`;
   - the owner asks where it stands: report each issue and its worker in `live`.
5. `resolve` the parent with a summary, delete your mission, then `close` each worker and `clean`.

# Work

1. `read` the issue and its parent, and `claim` the issue; held by another session, `comment` that on the issue and stop.
2. Write your mission.
3. Implement, run the repository's own checks, commit and push, and open the `pr` at the first push.
   Launch subagents only to split research or to edit different files at once in your worktree, since they share its branch and one file edited twice is overwritten. Work that needs its own pull request is the leader's to `file` and `start`: ask for it as a decision that is not yours, below.
4. Write the checks you ran into the `pr` body, then launch the `reviewer` on the pull request's url. `Findings`: fix, push, and resume that reviewer with `SendMessage` `see <pr-url>`, launching a new one when it cannot be resumed. `Approved <head>`: `merge`; refused by GitHub, merge the default branch in, push, and resume it the same way. Merged: `prompt` the leader `see <pr-url>` and delete your mission.

A decision that is not yours: `comment` `BLOCKED: <question>` on the issue, `prompt` the leader `see <issue-url>`, and stop until it prompts you back.
