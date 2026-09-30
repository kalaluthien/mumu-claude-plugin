---
type: regex
target: {source: file, path: verdict-66.txt}
match: contains
flags: i
pattern: '(D5|D1-D[5-9])[^\n]*(pass(es|ing)?( already)? (on|there)|already pass|cannot (be )?run|can ?not (be )?run|unrunnable|prints? (nothing|no line)|does not fail|nothing to score|cannot (be )?scored|no (lenses|anchors))'
---
