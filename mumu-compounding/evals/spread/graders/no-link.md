---
type: llm
focus: last_message
criteria: >-
  The eval sandbox denies the config directory, so the reply is expected to say it could not write and to print the edits or commands instead; judge what they would do, a printed command or edit counting as if it ran, one made conditional on the file not already saying it counting too. The config directory is the folder holding `projects/`, often a temporary path such as `/private/tmp/<x>/config`. Pass unless a line the reply adds, or prints for adding, to the config directory's `CLAUDE.md` is only a link or url.
---
