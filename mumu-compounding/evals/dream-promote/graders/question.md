---
type: llm
focus:
  source: file
  path: question-1.json
criteria: >-
  This JSON is the input for one AskUserQuestion call. Pass if the questions array has exactly one question, its multiSelect is true, and it has 2 to 4 options. Fail otherwise.
---
