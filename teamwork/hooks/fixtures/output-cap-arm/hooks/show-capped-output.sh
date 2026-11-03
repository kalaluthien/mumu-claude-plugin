#!/bin/sh
# Show a Bash call's saved output: whole when 50 lines or fewer, else the first 40 and last 10 lines and a note naming the
# file that keeps all of it; exit with the call's status. cap-bash-output.py's rewrite runs it from an EXIT trap.
# usage: show-capped-output.sh <status> <output-file>
[ $# -eq 2 ] || { echo "usage: show-capped-output.sh <status> <output-file>" >&2; exit 2; }
lines=$(wc -l <"$2" | tr -d ' ')
if [ "$lines" -gt 50 ]; then
  head -n 40 "$2"
  echo "[output cap: $((lines - 50)) of $lines lines cut here; all of them are in $2; read a range of that file, not all of it]"
  tail -n 10 "$2"
else
  cat "$2"
  rm -f "$2"
fi
exit "$1"
