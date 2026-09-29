---
type: regex
target: {source: file, path: guide.html}
match: contains
flags: s
pattern: ^(?=.*<main(?:(?!data-widget=).)*<[a-z]+(?=[^>]*\sdata-diagram="file-tree")[^>]*\sdata-widget="diagram".*?<details)(?=(?:.*<section[^>]*\sdata-chapter){3})(?=.*addEventListener\('hashchange', show\))(?=.*<dfn[^>]*\sid="([^"]+)".*?href="#\1")
---
