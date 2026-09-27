---
# three entries: the two kept, one ADD for npm ci, no new file for the storybook lesson
type: regex
target: {source: file, path: pool/MEMORY.md}
match: contains
flags: i
pattern: '^(?=[\s\S]*npm ci)(?=[\s\S]*pitfall-tz\.md)(?=[\s\S]*pitfall-dev-port\.md)(?![\s\S]*\n- [\s\S]*\n- [\s\S]*\n- )'
---
