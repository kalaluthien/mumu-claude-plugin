---
# (b) the kept pool files still hold the fact-ci-cache.md half: the lockfile key
type: regex
target: {source: file, path: pool-after.txt}
match: contains
pattern: 'package-lock'
---
