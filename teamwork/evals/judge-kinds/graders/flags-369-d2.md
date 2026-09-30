---
type: regex
target: {source: file, path: verdict-369.txt}
match: contains
flags: i
pattern: '(D2|D1-D[2-9])[^\n]*(pass(es|ing)?( already)? (on|there)|already pass|cannot (be )?run|can ?not (be )?run|unrunnable|prints? (nothing|no line)|does not fail|(no|without) ((on-)?main )?output (is )?quoted|quotes? no ((on-)?main )?output)'
---
