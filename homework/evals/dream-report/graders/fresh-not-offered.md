---
# matches only a body that never names the fresh lesson
type: regex
target: {source: file, path: issue-body.md}
match: contains
pattern: '^(?![\s\S]*feedback-lint-first)'
---
