---
# the body names the stale file and a cost
type: regex
target: {source: file, path: issue-body.md}
match: contains
pattern: '^(?=[\s\S]*fact-old-port)(?=[\s\S]*\d+ (?:files?|lines?))'
---
