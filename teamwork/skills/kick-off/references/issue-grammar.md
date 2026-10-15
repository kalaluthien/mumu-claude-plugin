# Issue grammar

How a teamwork issue is written, so a person reads it as prose and code composes its state from it. [issue_state.py](../../../lib/issue_state.py) loads the tables below; a keyword or key exists only here, and code names only a row's role.

## Append-only

- **Body**: written once, when the issue is filed, in free Markdown; never edited.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, `DECIDED: …`; the rest is free Markdown. A keyword says what the comment does to the issue, never who spoke; name a source in the content, `owner said: …`.
- **Latest wins**: a later record replaces an earlier one of the same role; nothing is edited or deleted.

## Keywords

| keyword | the comment | role |
| --- | --- | --- |
| `AMENDED` | adds to the issue's intent, its source named and its words quoted | |
| `BLOCKED` | asks a question with its options; the asker waits on the answer | ask |
| `DECIDED` | answers, routes or orders; binding until a newer one | answer |
| `REPORTED` | holds a report: findings, each citing its source | |
| `RESOLVED` | closes the issue with a summary of what landed or why it stopped | |

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
