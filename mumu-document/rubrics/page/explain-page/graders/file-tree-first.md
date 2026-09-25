---
type: regex
target: {source: file, path: tiny-queue.html}
match: contains
flags: s
---
<main(?:(?!data-widget=).)*data-widget="file-tree".*?<details
