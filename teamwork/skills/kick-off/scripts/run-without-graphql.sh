#!/bin/bash
# usage: run-without-graphql.sh <command>...
# Runs the command with a `gh` first on PATH that refuses every GraphQL-backed call and passes the rest to the real `gh`,
# so a script that still reads by GraphQL fails where it would otherwise spend a point.
set -e
real=$(command -v gh)
shim=$(mktemp -d)
trap 'rm -rf "$shim"' EXIT
cat > "$shim/gh" <<SHIM
#!/bin/bash
case "\$1 \$2" in
  "api graphql"|"issue "*|"pr "*|"repo "*|"label "*) echo "gh: GraphQL refused: \$*" >&2; exit 1;;
esac
exec "$real" "\$@"
SHIM
chmod +x "$shim/gh"
PATH="$shim:$PATH" "$@"
