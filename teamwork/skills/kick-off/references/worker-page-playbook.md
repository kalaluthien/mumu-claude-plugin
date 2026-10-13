# Page

Open when your work changes a page, a playbook's page form, the base page or a page check, such as `check-page.py`.

1. Load `paperwork:show-me`.
2. Change a fixture page first, then the pages that use it.
3. Run `check-page.py <page> --shots <dir>` on each changed page, and a zoom diagram's `make-diagram.py make` on each example it touches; hand a run over a few minutes to a subagent on `haiku` at `low` that reports only its failures.
4. Look at each page's 390 px and 1200 px captures; past 3 pages, one read-only subagent per page on `sonnet` at `medium`.

Done when `check-page.py` prints `ok` for each changed page, the touched examples print `ok`, and each capture shows the change.
