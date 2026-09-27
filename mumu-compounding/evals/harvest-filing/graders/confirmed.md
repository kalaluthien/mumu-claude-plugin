---
# CONFIRM: the TZ entry's count raised, no new file for it
type: regex
target: {source: file, path: pool/pitfall-tz.md}
match: contains
pattern: 'confirmed: 2'
---
