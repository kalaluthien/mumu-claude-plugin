---
type: llm
---

Pass only if the reply's plan does all three:
- Before its first edit to the skill, it runs the unchanged skill to record a baseline score to compare against (last night's number alone is not a baseline run).
- Before its first edit, it sets aside some of the 24 cases as a held-out set whose failures it does not read or tune on, and judges each change by the held-out cases' score.
- It makes one change per round, measured before the next, rather than several fixes at once.

Fail when any one is missing, including a plan that reads every failing case and fixes them together.
