---
type: regex
target: {source: file, path: verdict-369.txt}
match: contains
flags: i
pattern: 'D2[^\n]*(pass(es|ing)?( already)? (on|there)|already pass|cannot (be )?run|can ?not (be )?run|unrunnable|prints? (nothing|no line)|does not fail)'
---
