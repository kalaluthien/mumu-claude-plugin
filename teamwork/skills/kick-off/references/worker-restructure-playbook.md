# Restructure

Open when your work renames, moves, splits, merges or cuts files to a size or a convention, with no change of behaviour.

1. List every reference, `git grep -nw <old>`, and count them; past 50 files, one `Explore` subagent per folder on `haiku` at `low`.
2. `git mv`, then replace by script, never file by file.
3. Rerun the suite, and `claude plugin validate ./<plugin>` for a plugin.
4. Probe the installed or live copy that loads the moved files.
5. `git diff -M --numstat origin/<default>` shows only moves and replaced lines.

Done when `git grep` of each old name finds nothing and the suite passes as many tests as on main.
