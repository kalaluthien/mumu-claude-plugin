---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Skill]
---

Here is report.py:

```python
def weekly(rows):
    total = 0
    for r in rows:
        if r["status"] == "paid":
            total += r["amount"] * (1 + r["tax"])
    return round(total, 2)


def monthly(rows):
    total = 0
    for r in rows:
        if r["status"] == "paid":
            total += r["amount"] * (1 + r["tax"])
    return round(total, 2)
```

The two functions repeat the same loop. Pull it into one helper both call, keeping what each returns exactly as it is, and write the file.
