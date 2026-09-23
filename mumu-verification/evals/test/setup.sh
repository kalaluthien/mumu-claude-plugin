#!/bin/sh
cat > todo.py <<'PY'
import json, pathlib, sys

STORE = pathlib.Path("todo.json")


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else []


def add(title):
    items = load()
    items.append({"title": title})
    STORE.write_text(json.dumps(items))


def main(argv):
    if argv[:1] == ["add"]:
        add(argv[1])
    elif argv[:1] == ["list"]:
        for item in load():
            print(item["title"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
PY
