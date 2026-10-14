# UI

1. For a paperwork page or diagram, read `paperwork/skills/show-me/SKILL.md` and the playbook it routes the page to.
2. Change a fixture page or screen first, then what uses it.
3. Run the render check on each changed page or screen until it prints `ok`: `check-page.py <page> --shots <dir>`, `make-diagram.py make` on each zoom-diagram example touched; a run over a few minutes goes to a subagent.
4. Look at each 390 px and 1200 px capture until it shows the change; past 3 pages, one read-only subagent per page.
