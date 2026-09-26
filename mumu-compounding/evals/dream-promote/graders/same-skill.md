---
type: regex
target: {source: file, path: tools/skills/release/SKILL.md}
match: contains
pattern: '^-{3}\nname: release\ndescription: Cuts a release\.\n-{3}\n\n1\. Bump the version in package\.json\.\n2\. Tag the commit and push the tag\.\n$'
---
