---
type: regex
target: {source: file, path: trend.html}
match: contains
flags: is
pattern: ^(?=.*<figure(?=[^>]*\sdata-widget="chart")(?=[^>]*\sdata-chart="line")[^>]*>.*?<table.*?<thead)(?!.*data-chart="line"(?:(?!</figure>).)*(?:class="[^"]*\b(?:legend|key)\b|범례))
---
