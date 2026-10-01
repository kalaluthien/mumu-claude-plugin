---
# one backlog issue in the owning repository
type: regex
target: {source: file, path: gh.txt}
match: contains
pattern: '^(?=[\s\S]*issue create(?=[^\n]*example/tools)(?=[^\n]*backlog))(?![\s\S]*issue create[\s\S]*issue create)'
---
