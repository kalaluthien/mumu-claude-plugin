---
name: kickoff
description: Lead a goal to reviewed, merged pull requests, or work one issue of it. A goal makes this session the leader; `work <issue-url> leader <address>` makes it a worker.
disable-model-invocation: true
argument-hint: <goal> | work <issue-url> leader <address>
---

Arguments: $ARGUMENTS

Arguments of the shape `work <issue-url> leader <address>` make you a worker (§ Work); any others are a goal you lead (§ Lead).

`panes.md` drives other sessions and `repo.md` holds issues, branches and pull requests; each maps the verbs below to commands.

First check `ready`; when it fails, stop and print its fix.

Your mission is `${CLAUDE_PLUGIN_DATA}/mission/${CLAUDE_SESSION_ID}.md`, which a hook shows you every turn and every agent you launch at its start:

```
Goal: <the parent goal in words, not its url>
Mission: <your role, and your issue's url>
Expect: <the owner's expectations>; <your role's rules below>
```

# Domain

| term | meaning |
| --- | --- |
| leader | the session the owner talks to; it writes no code |
| worker | a session on one issue in its own worktree |
| reviewer | the `reviewer` agent: it reviews a plan or a pull request it did not write, and alone writes `Approved` |
| issue | one sub-issue of the parent: one worker, one branch, one pull request, all named `<topic>-<issue>` |
| topic | 2-4 lowercase words joined by hyphens |
| name | one string for a session's tab, herdr agent and Claude session: `<topic>-<issue>` for a worker, `<topic>-lead` for the leader |
| checkout | the local clone of the repository an issue lands in |
| claim | the branch on the remote; it exists, so the issue is taken |
| approval | a comment whose first line is `Approved <sha>`, valid while the head is that sha |
| `BLOCKED: <question>` | an issue comment asking for a decision that is not the worker's |
| `see <url>` | every prompt between sessions after the assignment: `read` the url now |

Rules:

- A merge happens only at an approved sha, and a hook refuses any other.
- A commit on the default branch, or a push to it, is refused by a hook in the checkout.
- Every session and agent runs Opus: effort low when its task names what to change and how to check it, medium when it does not.
- The owner is asked only architecture, infrastructure and user-experience questions; the rest is decided and written in the parent issue.
- Before building, read the prior work in the repository and its issues, the official docs and a web example.

# Lead

1. `name` yourself `<topic>-lead`, the topic being the goal's, then ask the owner every question at once with `AskUserQuestion`.
2. `file` the parent (the goal, the decisions, the expectations, the definition of done) and one issue per pull request, each labelled with its effort, then write your mission; launch the `reviewer` on the parent's url and fix its findings until it posts `Approved`.
3. For each issue: `checkout`, `start` it under its name at its effort, `watch` it, and `prompt` it `/orchestration:kickoff work <issue-url> leader <your address>`.
4. Poll nothing; act on what arrives:
   - `see <issue-url>` naming a `BLOCKED:` comment: `comment` the answer, then `prompt` the worker `see <issue-url>`;
   - `see <pr-url>`: that pull request merged; with no issue open, go to 5;
   - a `watch` returns: a worker at a permission prompt is the owner's to clear, so tell the owner and `watch` it again once cleared; a worker gone while its issue is open is `start`ed again in its worktree, resuming, and watched;
   - the owner changes direction: `comment` the change on each issue affected and `prompt` its worker `see <issue-url>`;
   - the owner asks where it stands: report each issue and its worker in `live`.
5. `resolve` the parent with a summary, `close` each worker, `clean`, and delete your mission.

# Work

1. `read` the issue and its parent, and `claim` the issue; held by another session, `comment` that on the issue and stop.
2. Write your mission.
3. Implement, run the repository's own checks, commit and push, and open the `pr` at the first push.
4. Launch the `reviewer` on the pull request's url. `Findings`: fix, push, launch it again. `Approved <head>`: `merge`; refused by GitHub, merge the default branch in, push, and launch it again. Merged: `prompt` the leader `see <pr-url>` and delete your mission.

A decision that is not yours: `comment` `BLOCKED: <question>` on the issue, `prompt` the leader `see <issue-url>`, and stop until it prompts you back.
