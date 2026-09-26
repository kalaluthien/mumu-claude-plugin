---
type: llm
focus:
  source: file
  path: question-1.json
criteria: >-
  This is the input for one AskUserQuestion call. Pass if it holds exactly one question with multiSelect true and 2 to 4 options, and one option, by its label or its description, moves the lesson kept in both feedback-recommend-one.md and tip-pick-one.md into CLAUDE.md or deletes a copy of it. Fail if it holds more than one question, fewer than 2 or more than 4 options, multiSelect is not true, or no option covers that shared lesson.
---
