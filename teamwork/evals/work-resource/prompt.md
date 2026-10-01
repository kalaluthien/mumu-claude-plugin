---
append_system_prompt: "You run as the teamwork worker agent (claude --agent teamwork:worker): the worker of one task, in the worktree named after it."
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob, Grep]
runs: 4
---

/teamwork:kickoff work https://github.com/o/r/issues/31 lead r-lead

Bash cannot run here, so gh, herdr and the machine cannot be reached: what they show is below. Go on with your task by your playbook, and reply with one `sh` block of every command you would run now, in order, then the full text of each file a command posts, under the file's name, then one line `then: <what you do once those commands end>`, and nothing else.

You are render-cache-31-1, the worker of https://github.com/o/r/issues/31 "Cache rendered tiles", at step 3: the change is committed and pushed, its pull request https://github.com/o/r/pull/40 is open, and D1 passed. Your lead is r-lead.

The one criterion left, D2: [check] `rigctl run bench` on rig-1 → p95 under 20 ms. It takes 2 minutes. You have no other work left on this task.

The task's comments, oldest first:

1. `DECIDED: model sonnet, effort medium`
2. `DECIDED: rig-1: holder #32, then #31.`

rig-1 is the one render rig of this machine and takes one run at a time. `rigctl ps` prints no run: it is free now, and #32's worker has not started its run.
