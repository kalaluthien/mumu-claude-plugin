---
# the stale file is still on disk
type: regex
target: {source: file, path: stale-after.txt}
match: contains
pattern: 'port 5173'
---
