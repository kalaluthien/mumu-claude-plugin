# Migration

1. List every reference or user of the old form, `git grep -nw <old>`, and count them; past 50 files, one `Explore` subagent per folder on `haiku` at `low`.
2. For data, a schema or a live service, copy it first and dry-run the change on the copy.
3. `git mv`, then replace by script, never file by file.
4. Rerun the suite until it passes as many tests as on main, and `claude plugin validate ./<plugin>` for a plugin.
5. Probe the installed or live copy that loads the moved files or data.
6. `git diff -M --numstat origin/<default>` shows only moves and replaced lines, and `git grep` of each old name finds nothing.
