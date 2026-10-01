---
# the dangling line is gone, the live one kept
type: regex
target: {source: file, path: config/projects/-a/memory/MEMORY.md}
match: contains
pattern: '^(?=[\s\S]*\(fact-dev-port\.md\))(?![\s\S]*fact-old-deploy)'
---
