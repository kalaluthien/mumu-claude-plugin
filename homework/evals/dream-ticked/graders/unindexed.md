---
# the ticked file left its index, the fresh one kept
type: regex
target: {source: file, path: config/projects/-tools/memory/MEMORY.md}
match: contains
pattern: '^(?=[\s\S]*\(feedback-lint-first\.md\))(?![\s\S]*fact-old-port)'
---
