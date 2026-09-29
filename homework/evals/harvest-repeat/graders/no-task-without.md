---
# the task names neither the new build lesson nor the notes lesson
type: regex
target: {source: file, path: handoff-1.md}
match: contains
flags: i
pattern: '^(?![\s\S]*(npm ci|editor))'
---
