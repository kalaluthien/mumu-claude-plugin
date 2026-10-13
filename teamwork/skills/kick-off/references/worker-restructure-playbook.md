# Restructure

1. List every reference, `git grep -nw <old>`, and count them; past 50 files, one `Explore` subagent per folder on `haiku` at `low`.
2. `git mv`, then replace by script, never file by file.
3. Rerun the suite until it passes as many tests as on main, and `claude plugin validate ./<plugin>` for a plugin.
4. Probe the installed or live copy that loads the moved files.
5. `git diff -M --numstat origin/<default>` shows only moves and replaced lines, and `git grep` of each old name finds nothing.
