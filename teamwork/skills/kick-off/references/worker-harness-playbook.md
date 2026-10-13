# Harness

Open when your work changes rule files (skills, playbooks, rubrics, `AGENTS.md`) or code (scripts, hooks, monitors, `lib/`, `bin/`); a test or eval case goes with what it checks.

1. Take the track of the larger share of changed lines, the other at its first edit.
2. **Rules track**: `git grep` every file that states the rule; past 5 files, an `Explore` subagent on `haiku` at `low` lists them. Edit the rule where it lives, check any size cap with `git diff --numstat origin/<default>`, and run each criterion over the lines that carry the rule, not over the diff.
3. **Script track**: write the failing test or probe first and keep its output on main; implement; run the plugin's tests; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
4. A hook, monitor or start script: probe the live copy in a new session, never only its fixture.

Done when each criterion passes at head and its test or probe fails on main.
