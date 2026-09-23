---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Our order service moves an order through placed, paid, shipped and refunded. I want to add partial refunds. Before touching the code, how do we make sure an order can never be both shipped and fully refunded?
