---
name: lead
description: Use when this session leads work split across worker sessions - after /kickoff, or when told it is the leader - to file the issues, launch workers in herdr panes, answer BLOCKED, relaunch a dead worker, and finish. Not for doing one issue yourself (work).
---

# Lead

You file, launch, answer and finish. You write no code. Workers land PRs; a merge needs the reviewer's `Approved <sha>`, which a hook checks.

## 1. Ask once

Put every architecture, infrastructure and UX question the goal raises into one `AskUserQuestion` round. Decide the rest yourself and state each decision in the parent issue.

## 2. File

- The repo the work lands in holds the issues. Two repos moving together: the parent goes on `kalaluthien/workspace`.
- Parent issue: the goal, the decisions, the definition of done.
- One issue per unit of work (one PR), linked as a sub-issue: `gh issue create -R <repo> --parent <parent-url> --label effort:<low|medium> ...`. Create the label if missing.
- Each issue body: what to change, how to check it, which repo.

## 3. Mission

Write your own mission file: `mission path leader` prints where, from the checkout you lead in. 3-5 lines:

```
Goal: <parent goal> (<parent url>)
Role: leader; I file, launch, answer BLOCKED, finish; I write no code.
Expect: every unit lands as a PR merged at an approved sha; ask the owner only preference, scope, destructive stakes.
```

## 4. Launch

One worker per issue, each in its own worktree and herdr pane, per `herdr.md`: add the worktree `<checkout>/.claude/worktrees/<issue>-<topic>` of the repo's checkout (`~/workspace/projects/<repo>`, or `~/workspace` for kalaluthien/workspace), start `claude --model opus --effort <the issue's effort label>` in it, then prompt `work <issue-url> leader <your pane>`.

## 5. Answer

- A `BLOCKED: <question>` comment arrives with a prompt in your pane. Answer on the issue, then prompt the worker's pane: `answered on <issue-url>`.
- `merged <pr-url>` arrives in your pane when a worker lands its PR; no sub-issue open -> step 6.
- Poll nothing.
- A worker gone from `herdr agent list` while its issue is open: relaunch it on the same branch (`herdr.md`, relaunch).

## 6. Finish

When no sub-issue under the parent is open:
- close the parent with a summary comment;
- `git worktree remove` each worker's worktree; delete local branches already on origin;
- close the workers' panes (`herdr.md`); remove your mission file (`mission path leader`).
