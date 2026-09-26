---
type: regex
target: {source: file, path: question-1.json}
match: contains
flags: i
pattern: '"label":\s*"[^"]*\b(file|task|issue)\b[^"]*release'
---
