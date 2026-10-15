# Issue grammar

How a teamwork issue is written, so a person reads it as prose and code composes its state from it. [issue_state.py](../../../lib/issue_state.py) loads the tables below; a keyword or key exists only here, and code names only a row's role.

## Append-only

- **Body**: written once, when the issue is filed, in free Markdown; never edited.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, then the kind of work it records in plain words after the keyword, `REPORTED: batch landed …`; the rest is free Markdown. A keyword says what the comment does to the issue, never who spoke; name a source in the content, `owner said: …`.
- **Fewest keywords**: a kind of work gets a keyword of its own only when code must tell it apart or its category differs wholly; comments posted under words no longer listed stay as written, read as prose.
- **Latest wins**: a later record replaces an earlier one of the same role; nothing is edited or deleted.

## Keywords

| keyword | the comment | role |
| --- | --- | --- |
| `BLOCKED` | asks a question with its options; the asker waits on the answer | ask |
| `DECIDED` | binds until a newer one: answers, routes, orders, or adds intent, its source named and its words quoted | answer |
| `REPORTED` | informs: findings each citing its source, a batch landed with the backlog left open, or a close summary; open or closed is GitHub's state | |

## Data

Data a script reads sits only in a fenced block whose info string is `teamwork`, one `key: value` per line; explanation never uses that fence, so prose never parses as data. A body or any comment may carry one.

````markdown
DECIDED: issue-pane-worker holds this.

```teamwork
holders: issue-pane-worker
```
````

| key | value | role |
| --- | --- | --- |
| `holders` | session names, space-separated, replacing every earlier value; empty when no one holds it | holders |
| `asks` | `owner` on an ask the owner answers, not the manager | audience |

## Waits

What an open issue waits on, first match:

1. an open issue GitHub lists as blocking it: `blocked by #<n>`;
2. its latest ask or answer is an ask: `waits on the owner` with audience `owner`, else `waits on the manager`;
3. no names in its latest holders: `no holder`;
4. else `held`.
