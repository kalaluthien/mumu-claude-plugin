---
# (b) the kept pool files still hold the pitfall-ci-cache-npmrc.md half: the rebuild step
type: regex
target: {source: file, path: pool-after.txt}
match: contains
pattern: 'CACHE_VERSION'
---
