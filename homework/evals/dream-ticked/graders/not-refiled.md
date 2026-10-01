---
# the ticked fix is not filed again
type: regex
target: {source: file, path: gh.txt}
match: contains
pattern: '^(?![\s\S]*issue create)'
---
