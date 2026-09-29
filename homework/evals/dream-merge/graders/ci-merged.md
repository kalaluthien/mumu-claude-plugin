---
# (b) two halves of one mechanism: exactly one of them is still indexed
type: regex
target: {source: file, path: config/projects/-a/memory/MEMORY.md}
match: contains
pattern: '^(?=[\s\S]*\((?:fact-ci-cache|pitfall-ci-cache-npmrc)\.md\))(?![\s\S]*fact-ci-cache\.md[\s\S]*pitfall-ci-cache-npmrc\.md)(?![\s\S]*pitfall-ci-cache-npmrc\.md[\s\S]*fact-ci-cache\.md)'
---
