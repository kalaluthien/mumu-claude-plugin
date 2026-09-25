---
type: regex
target: {source: file, path: trend.html}
match: contains
flags: s
---
<figure(?=[^>]*\sdata-widget="chart")(?=[^>]*\sdata-chart="line")[^>]*>.*?<table.*?<thead
