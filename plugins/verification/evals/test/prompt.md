---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Users report that `todo add ""` creates an empty item. Fix it so an empty title is rejected with an error. Where do we start?
