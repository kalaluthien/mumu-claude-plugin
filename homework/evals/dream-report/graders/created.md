---
# title and labels as dream names them
type: regex
target: {source: file, path: gh.txt}
match: contains
pattern: 'issue create(?=[^\n]*Confirm dream fixes)(?=[^\n]*backlog)(?=[^\n]*scope:homework)'
---
