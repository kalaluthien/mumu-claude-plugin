---
type: regex
target: {source: file, path: trend.html}
match: not_contains
flags: is
---
data-chart="line"(?:(?!</figure>).)*(?:class="[^"]*\b(?:legend|key)\b|범례)
