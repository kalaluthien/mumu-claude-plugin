# UI

1. For a paperwork page or diagram, load `paperwork:show-me`.
2. Change a fixture page or screen first, then what uses it.
3. Run the render check on each changed page or screen until it prints `ok`, such as `check-page.py <page> --shots <dir>` or a zoom diagram's `make-diagram.py make` on each example it touches; hand a run over a few minutes to a subagent on `haiku` at `low` that reports only its failures.
4. Look at each 390 px and 1200 px capture until each shows the change; past 3 pages, one read-only subagent per page on `sonnet` at `medium`.
