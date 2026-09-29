---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Skill]
---

You are a worker on one task, in its own worktree. Follow these steps in order:
1. Read the task below.
2. Implement it: write the changed file.
3. Commit with `git add -A && git commit -m "<title>"` and reply with the commit's one-line summary.

## Task #41: Keep one reviewer per pull request

Our Claude Code plugin's reviewer runs as the subagent defined in `agents/reviewer.md`, whose body ends:

```markdown
# Rules

- Review only what you did not write.
- Post `FINDINGS:` with one line per defect, or `APPROVED: <sha>`.
```

Two reviewers sometimes post on the same pull request at once. Add a rule so a reviewer stops without posting when another reviewer's verdict is already on the pull request at the same head, and write the file.
