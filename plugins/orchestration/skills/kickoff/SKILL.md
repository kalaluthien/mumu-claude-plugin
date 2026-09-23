---
name: kickoff
description: Lead a goal to reviewed, merged pull requests, or work one issue of it. A goal makes this session the leader; `work <issue-url> leader <address>` makes it a worker.
disable-model-invocation: true
argument-hint: <goal> | work <issue-url> leader <address>
---

Arguments: $ARGUMENTS

Arguments starting with `work` make you a worker (§ Work); any others are a goal you lead (§ Lead).

Before anything else, write your mission to `${CLAUDE_PLUGIN_DATA}/mission/${CLAUDE_SESSION_ID}.md`. A hook shows it to you every turn and to every agent you launch:

```
Goal: <the parent goal, in words>
Mission: <your role, and your issue's url>
Expect: <the owner's expectations>; <your role's rules below>
```

`panes.md` drives other sessions and `repo.md` holds issues, branches and pull requests; each maps the verbs below to commands.

# Domain

| term | meaning |
| --- | --- |
| leader | the session the owner talks to: it asks, files, launches, answers, redirects and finishes, and writes no code |
| worker | a session on one issue in its own worktree: it decomposes, researches, experiments and lands one pull request |
| reviewer | the `reviewer` agent: it reviews a plan or a pull request it did not write, and alone writes `Approved` |
| issue | one sub-issue of the parent: one worker, one branch, one pull request, all named `<topic>-<issue>` |
| claim | the branch on the remote; it exists, so the issue is taken |
| approval | a comment whose first line is `Approved <sha>`, valid while the head is that sha |
| `BLOCKED: <question>` | an issue comment asking for a decision that is not the worker's |
| `see <url>` | every prompt between sessions after the assignment: read what the url says now |

Rules:

- A merge happens only at an approved sha, and a hook refuses any other.
- A commit on the default branch is refused by the repository's commit hook.
- Every session and agent runs Opus: effort low when its task names what to change and how to check it, medium when it does not.
- The owner is asked only architecture, infrastructure and agent-experience questions, all at once; the rest is decided and written in the parent issue.

# Lead

1. Ask the owner every question at once with `AskUserQuestion`.
2. `file` the parent (the goal, the decisions, the expectations, the definition of done) and one issue per pull request, each labelled with its effort; launch the `reviewer` on the parent's url and fix its findings until it posts `Approved`.
3. For each issue: `checkout`, `start` at its effort, and `prompt` it `/orchestration:kickoff work <issue-url> leader <your address>`.
4. Poll nothing; act on what arrives:
   - `see <issue-url>` with a question: answer on the issue, then `prompt` the worker `see <issue-url>`;
   - `see <pr-url>`: that pull request merged; with no issue open, go to 5;
   - the owner changes direction: edit the issues affected and `prompt` each of their workers `see <issue-url>`;
   - the owner asks where it stands: report each issue and its worker in `live`, and `start` a worker gone while its issue is open again in its worktree, resuming, with the same assignment.
5. Close the parent with a summary, `close` each worker, `clean`, and delete your mission.

# Work

1. Write your mission from the issue and its parent.
2. `claim` the issue; held by another session, say so on the issue and stop.
3. Implement, run the repository's own checks, commit and push, and open the `pr` at the first push.
4. Launch the `reviewer` on the pull request's url. `Findings`: fix, push, launch it again. `Approved <head>`: `merge`, then `prompt` the leader `see <pr-url>`.

A decision that is not yours: post `BLOCKED: <question>` on the issue, `prompt` the leader `see <issue-url>`, and stop until it prompts you back.
