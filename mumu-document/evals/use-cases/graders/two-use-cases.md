---
type: regex
target: {source: file, path: flows.html}
match: contains
flags: s
pattern: ^(?=(?:.*\sdata-diagram="use-case"){2})(?!(?:.*\sdata-diagram="use-case"){3})
---
