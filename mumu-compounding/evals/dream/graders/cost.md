---
type: llm
focus:
  source: file
  path: question-1.json
criteria: >-
  This is the input for one AskUserQuestion call. Pass if the description of every option other than one labelled None states the fix's cost as a number of files or lines it touches, such as "2 files" or "3 lines". Fail if any such option's description gives no number of files or lines.
---
