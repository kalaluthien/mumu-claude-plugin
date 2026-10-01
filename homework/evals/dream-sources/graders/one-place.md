---
type: llm
focus: 
  source: file
  path: rule.txt
criteria: >-
  This file is tools/AGENTS.md, then after the === line tools/skills/release/SKILL.md. Pass if the rule that commit messages start with a verb is stated in exactly one of the two files. Fail if both state it or neither does.
---
