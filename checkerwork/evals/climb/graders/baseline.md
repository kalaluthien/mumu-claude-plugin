---
# a baseline run of the unchanged skill, not last night's number
type: regex
match: contains
flags: i
pattern: '(re-?run|run|measure|record|get)[^.\n]{0,60}(baseline|unchanged)|(baseline|unchanged)[^.\n]{0,40}\brun\b|fresh baseline|new baseline'
---
