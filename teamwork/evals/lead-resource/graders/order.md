---
type: regex
target: last_message
match: contains
flags: i
pattern: '#32[^\n]*(after it|then|first|before|next)[^\n]*#31|\| *1[^|\n]*\|[^\n]*#32[^\n]*\n\| *2[^|\n]*\|[^\n]*#31|(now|first|1st)[^\n]*#32[^\n]*\n[^\n]*(next|then|after|2nd)[^\n]*#31'
---
