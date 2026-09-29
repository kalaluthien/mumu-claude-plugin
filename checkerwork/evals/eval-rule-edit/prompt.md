---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Skill]
---

You are a worker on one task, in its own worktree. Follow these steps in order:
1. Read the task below.
2. Implement it: write the changed file.
3. Commit with `git add -A && git commit -m "<title>"` and reply with the commit's one-line summary.

## Task #88: Hold the reviewer until CI passes

Our Claude Code plugin runs a worker agent from `agents/worker.md`; the playbook it follows is `skills/kickoff/references/worker-playbook.md`, whose steps include:

```markdown
3. Implement, then rerun every criterion, commit, push, and open the pull request at the first push.
4. With every criterion passing, launch the reviewer on the pull request's url.
```

Workers keep launching the reviewer while CI is still red. Add a rule to step 4 so a worker waits for CI to pass first, and write the file.
