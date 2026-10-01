---
# the -b copy left its index
type: regex
target: {source: file, path: config/projects/-b/memory/MEMORY.md}
match: contains
pattern: '^(?![\s\S]*tip-pick-one)'
---
