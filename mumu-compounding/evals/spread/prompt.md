---
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob, Grep, Edit, Write, Bash]
runs: 3
---

Earlier in this project I saved to memory `feedback-shellcheck.md`: run `shellcheck` on a shell script before committing it, because a quoting bug slipped through review twice. That holds for all my projects, not just this one; remember it that way.
