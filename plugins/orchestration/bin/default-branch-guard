#!/bin/sh
# Git pre-commit and pre-push: refuse a commit on the repository's default
# branch and a push to it, so work lands only through a pull request.
# The default branch is origin's HEAD, else init.defaultBranch, else main.

default=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
default=${default#origin/}
[ -n "$default" ] || default=$(git config init.defaultBranch)
[ -n "$default" ] || default=main

refuse() {
  echo "$(basename "$0"): $1 the default branch \"$default\" is refused; land it through a pull request." >&2
  exit 1
}

if [ "$(basename "$0")" = pre-push ]; then
  while read -r _ _ remote_ref _; do
    [ "$remote_ref" = "refs/heads/$default" ] && refuse "a push to"
  done
  exit 0
fi
branch=$(git symbolic-ref --quiet --short HEAD) || exit 0  # detached: rebase, bisect
[ "$branch" = "$default" ] && refuse "a commit on"
exit 0
