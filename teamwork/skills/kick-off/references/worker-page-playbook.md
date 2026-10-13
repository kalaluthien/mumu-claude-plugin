# Page

Open when your work changes a rendered page, a widget, a skin or a page check, such as `check.py`.

1. Load `paperwork:rendering`.
2. Change a fixture page first, then the pages that use it.
3. Run `check.py` and the page tests at 320 px and at desktop width; hand a suite over a few minutes to a subagent on `haiku` at `low` that reports only its failures.
4. Read each changed render in Chrome, scrolled once to paint; past 3 fixtures, one read-only subagent per fixture on `sonnet` at `medium`.

Done when `check.py` is clean, the page tests pass, and each render shows the change.
