---
# matches only a file that never names the fresh lesson
type: regex
target: {source: file, path: question-1.json}
match: contains
pattern: '^(?![\s\S]*feedback-lint-first)'
---
