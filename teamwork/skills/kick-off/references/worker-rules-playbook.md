# Rules

1. `git grep` every file that states the rule; past 5 files, an `Explore` subagent lists them.
2. Edit the rule where it lives; check any size cap with `git diff --numstat origin/<default>`.
3. Run each criterion over the lines that carry the rule, not over the diff.
