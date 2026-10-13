# Recall

Open when you take new work, before you file an issue, and before you comment a `BLOCKED:`: the repository's history may already hold the answer, the decision or the attempt that failed.

1. Run [recall-work.py](../scripts/recall-work.py) with the work's words, adding `--path <file>` for each file you will change; it follows renames.
2. Read each line's kind and state: a `not planned` issue or a `closed` PR is an attempt stopped; learn why before you repeat it.
3. Treat each `DECIDED:` line as binding until a newer one replaces it; a `BLOCKED:` line is a question already asked, so find its answer below it.
4. `read` in full only the items whose lines bear on your work; rerun with other words when none does.
5. Cite in your task's Goal each item you build on, and in your question each decision it would change.

Done when each item that bears on your work is cited or set aside, and nothing you ask is settled by a `DECIDED:` you recalled.
