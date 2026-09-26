---
type: regex
target: {source: file, path: tiny-queue.html}
match: contains
flags: s
pattern: <main(?:(?!data-widget=).)*<[a-z]+(?=[^>]*\sdata-diagram="file-tree")[^>]*\sdata-widget="diagram".*?<details
---
