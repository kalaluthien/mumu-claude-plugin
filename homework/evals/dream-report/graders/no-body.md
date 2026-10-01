---
# the public body never quotes the memory
type: regex
target: {source: file, path: issue-body.md}
match: contains
pattern: '^(?![\s\S]*5173)'
---
