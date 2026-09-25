---
type: regex
target: {source: file, path: flows.html}
match: not_contains
flags: s
---
\sdata-widget="flow".*\sdata-widget="flow".*\sdata-widget="flow"
