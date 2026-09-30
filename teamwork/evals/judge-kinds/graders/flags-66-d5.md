---
type: regex
target: {source: file, path: verdict-66.txt}
match: contains
flags: i
pattern: '(D5|D1-D[5-9])[^\n]*(pass(es|ing)?( already)? (on|there)|already pass|cannot (be )?run|can ?not (be )?run|unrunnable|prints? (nothing|no line)|does not fail|could(n.t| not) (be )?run|quotes? (nothing|no (failing )?((on-)?main )?output)|no (failing )?((on-)?main )?output (from main )?(is )?quoted|cannot (be )?scored|nothing (to score|measurable) on main|no ((failing|main) )?score (from |on )?(main )?(is )?quoted|no score (from|on) main)'
---
