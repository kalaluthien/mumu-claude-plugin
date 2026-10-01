---
# one open box names the stale file with its cost
type: regex
target: {source: file, path: issue-body.md}
match: contains
pattern: '(?:^|\n)- \[ \] [^\n]*fact-old-port[^\n]*\d+ (?:files?|lines?)'
---
