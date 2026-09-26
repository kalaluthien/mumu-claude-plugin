---
type: llm
focus:
  source: file
  path: question-1.json
criteria: >-
  This JSON is the input for one AskUserQuestion call. Pass if all hold: the questions array has exactly one question; its multiSelect is true; it has 1 to 4 options; and at least one option, by its label or its description, proposes filing a task or issue so that the release skill's SKILL.md gains the step of running npm test before tagging. Fail if any of these does not hold.
---
