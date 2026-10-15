# Migration

1. Count every reference or user of the old form, `git grep -nw <old>`; past 50 files, one `Explore` subagent per folder.
2. For data, a schema or a live service, dry-run the change on a copy first.
3. A test that forbids the old name builds it from joined pieces (`a + "-" + b`), or its own literal matches the grep.
4. `git mv`, then replace by script, never file by file.
5. Rerun the suite until it passes as many tests as on main; `claude plugin validate ./<plugin>` for a plugin.
6. Probe the installed or live copy that loads the moved files or data.
7. Done when `git diff -M --numstat origin/<default>` shows only moves and replaced lines, and `git grep` finds no old name.
