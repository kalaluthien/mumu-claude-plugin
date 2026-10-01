---
# no second line names the stale file
type: regex
target: {source: file, path: issue-body.md}
match: contains
pattern: '^(?![\s\S]*fact-old-port[^\n]*\n[\s\S]*fact-old-port)'
---
