---
type: regex
target: {source: file, path: verdict-369.txt}
match: contains
flags: i
pattern: '\bD2\b[^\n]*(pass|prints? (no|nothing)|no line|nothing|empty|already|\\b)[^\n]*\bmain\b|\bD2\b[^\n]*\bmain\b[^\n]*(pass|prints? (no|nothing)|no line|nothing|empty|already|\\b)'
---
