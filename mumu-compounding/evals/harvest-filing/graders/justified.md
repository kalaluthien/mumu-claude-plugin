---
# the ADD's one line: nearest entry, or none, and why; a regex, since the haiku judge failed such replies 2 runs in 3
type: regex
target: last_message
match: contains
flags: i
pattern: 'npm ci[\s\S]*(no (existing|other|saved) (entry|entries|memory|memories|note)|none of the (existing|saved)|nearest|closest|could(n''t| not) be extended|none could)'
---
