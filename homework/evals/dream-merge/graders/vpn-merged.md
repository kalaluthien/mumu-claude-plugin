---
# (a) one lesson in two files: exactly one of them is still indexed
type: regex
target: {source: file, path: config/projects/-a/memory/MEMORY.md}
match: contains
pattern: '^(?=[\s\S]*\((?:deploy-needs-vpn|pitfall-staging-vpn)\.md\))(?![\s\S]*deploy-needs-vpn\.md[\s\S]*pitfall-staging-vpn\.md)(?![\s\S]*pitfall-staging-vpn\.md[\s\S]*deploy-needs-vpn\.md)'
---
