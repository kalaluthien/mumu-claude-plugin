---
type: regex
target: {source: file, path: verdict-369.txt}
match: contains
flags: i
pattern: '(D2|D1-D[2-9])[^\n]*(pass(es|ing)?( already)? (on|there)|already pass|cannot (be )?run|can ?not (be )?run|unrunnable|prints? (nothing|no line)|does not fail|could(n.t| not) (be )?run|no (failing )?((on-)?main )?output (from main )?(is )?quoted|quotes? no (failing )?((on-)?main )?output)'
---
