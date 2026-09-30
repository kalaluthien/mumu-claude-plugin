---
type: regex
target: last_message
match: not_contains
flags: i
pattern: '```sh[^`]*(\bwhile\b|\buntil\b|\bsleep\b|\bwatch\b)|^then:[^\n]*(poll|every \d|check(ing)? again|re-?check|until (it|rig-1) is free|wait for (it|rig-1) to)'
---
