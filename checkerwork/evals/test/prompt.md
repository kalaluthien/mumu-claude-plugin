---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Skill]
---

Here is todo.py:

```python
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
```

Users report that `python todo.py add ""` creates an empty item. Fix it so a blank title is rejected with an error.
