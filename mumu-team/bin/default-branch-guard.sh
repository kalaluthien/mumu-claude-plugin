#!/bin/sh
# Git pre-commit: refuse a commit on the repository's default branch, so
# work lands only through a pull request and `pull --ff-only` stays clean.
# A push to it is refused by the server's ruleset (lib/gh.py's guard), so run
# as any other hook, such as pre-push, it passes: `push --delete` works on it.
# The default branch is origin's HEAD, else init.defaultBranch, else main.

default=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
default=${default#origin/}
[ -n "$default" ] || default=$(git config init.defaultBranch)
[ -n "$default" ] || default=main

refuse() {
  echo "$(basename "$0"): $1 the default branch \"$default\" is refused; land it through a pull request." >&2
  exit 1
}

[ "$(basename "$0")" = pre-commit ] || exit 0
branch=$(git symbolic-ref --quiet --short HEAD) || exit 0  # detached: rebase, bisect
[ "$branch" = "$default" ] && refuse "a commit on"
exit 0
