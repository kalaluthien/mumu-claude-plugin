---
type: llm
focus: last_message
criteria: Pass if the reply prints at least one shell command that copies a file from a path under backup/ back to its original path under config/, such as `cp 'backup/projects/-a/memory/feedback-recommend-one.md' 'config/projects/-a/memory/feedback-recommend-one.md'`. Fail if no such restore command is printed.
---
