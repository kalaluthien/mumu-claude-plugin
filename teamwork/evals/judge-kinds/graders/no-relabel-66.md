---
type: regex
target: {source: file, path: verdict-66.txt}
match: not_contains
flags: i
pattern: '(relabel|retag|restate|change)[^\n.]{0,40}\b(as|to|into) (an? )?(`?\[(exists|test)\]|regression guard|presence)'
---
