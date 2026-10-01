---
# the fix sits on another branch or in a backlog issue
type: regex
target: {source: file, path: after.txt}
match: contains
pattern: '(?:^|\n)[* ] +(?!main\n)\S|issue create[^\n]*backlog'
---
