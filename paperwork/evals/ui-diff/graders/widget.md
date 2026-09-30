---
type: regex
target: {source: file, path: cold-open.html}
match: contains
flags: s
pattern: <main\b.*<[a-z]+(?=[^>]*\sdata-widget="ui-diff")(?=[^>]*\sdata-slide[\s>=])[^>]*>.*?<ol class="steps">
---
