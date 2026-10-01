---
# the default branch gains no commit
type: regex
target: {source: file, path: main-log.txt}
match: contains
pattern: '^[0-9a-f]+ init\n$'
---
