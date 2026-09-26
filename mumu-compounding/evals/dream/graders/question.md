---
type: llm
focus:
  source: file
  path: question.json
criteria: >-
  This is the input for one AskUserQuestion call. Pass if it holds exactly one question with multiSelect true and 1 to 4 options, and one option's label names a move or delete of the lesson kept in both feedback-recommend-one.md and tip-pick-one.md, or an edit of CLAUDE.md for it, with a reason in its description. Fail if it holds more than one question, more than 4 options, multiSelect is not true, or no option covers that shared lesson.
---
