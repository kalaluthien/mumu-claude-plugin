---
type: regex
target: last_message
match: not_contains
flags: m
pattern: '^rigctl ps|^[^\n`]*\b(while|until|for|sleep|watch)\b[^\n`]*\b(rigctl|gh|sleep)\b'
---
