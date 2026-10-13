# Page

1. Load `paperwork:show-me`.
2. Change a fixture page first, then the pages that use it.
3. Run `check-page.py <page> --shots <dir>` on each changed page, and a zoom diagram's `make-diagram.py make` on each example it touches, until each prints `ok`; hand a run over a few minutes to a subagent on `haiku` at `low` that reports only its failures.
4. Look at each page's 390 px and 1200 px captures until each shows the change; past 3 pages, one read-only subagent per page on `sonnet` at `medium`.
