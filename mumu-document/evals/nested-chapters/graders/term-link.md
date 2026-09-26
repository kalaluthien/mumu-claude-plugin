---
type: regex
target: {source: file, path: guide.html}
match: contains
flags: s
pattern: <dfn[^>]*\sid="([^"]+)".*?href="#\1"
---
