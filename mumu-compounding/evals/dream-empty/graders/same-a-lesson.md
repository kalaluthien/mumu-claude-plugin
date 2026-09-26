---
type: llm
focus:
  source: file
  path: config/projects/-a/memory/pitfall-zsh-overwrite.md
criteria: Pass if the file's whole content is exactly the one line "In zsh write >| to overwrite a file, because noclobber is on.", with nothing added, removed or changed. Fail otherwise.
---
