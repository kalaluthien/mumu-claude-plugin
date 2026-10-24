# Issue grammar

How a teamwork issue is written, so a person reads it as prose and code composes its state from it. [issue_state.py](../../../lib/issue_state.py) loads the tables below; a keyword or key exists only here, and code names only a row's role.

## Rules

- **Body**: written when the issue is filed, in free Markdown; afterwards only its sections and its summary line change, and only by [edit-issue-body.py](../scripts/edit-issue-body.py), which first posts a comment holding the exact diff, then applies it.
- **Summary line**: a backlog body opens with one plain sentence that sums up the work, on one line, because the issue pane shows the body's first paragraph and nothing when it starts with `#`. The sentence carries no label (`**Summary:**`) and no quote header (`Owner said, verbatim:`). The owner's words and the rest follow. The owner's words change a backlog's scope often, so the manager rewrites the line and the title at each material change. A task's title sums it up, so its `Goal` opens with no summary; each criterion opens with its name, `1. [check] **<name>**: <details>`, because the pane shows the title and the names and folds the rest.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, then the kind of work it records in plain words after the keyword, `REPORTED: batch landed …`; the rest is free Markdown. A keyword says what the comment does to the issue, never who spoke; name a source in the content, `owner said: …`.
- **Fewest keywords**: a kind of work gets a keyword of its own only when code must tell it apart or its category differs wholly; comments posted under words no longer listed stay as written, read as prose.
- **Trusted authors**: only a body or comment by an author the board adapter trusts records anything; code reads any other as prose, since anyone may comment on a public board.
- **Latest wins**: a later record replaces an earlier one of the same role; no comment is edited or deleted.

## Keywords

| keyword | the comment | role |
| --- | --- | --- |
| `BLOCKED` | asks a question with its options; the asker waits on the answer | ask |
| `DECIDED` | binds until a newer one: answers, routes, orders, or adds intent, its source named and its words quoted | answer |
| `REPORTED` | informs: findings each citing its source, a batch landed with the backlog left open, or a close summary; open or closed is the board's state | |

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
| `deferred` | why someone chose to leave it for later; a later holders value with names ends it | deferral |
| `asks` | `owner` on an ask the owner answers, not the manager | audience |

## Sections

A task's sections, each a `## <section>` heading in the body, which holds their current text; a comment's heading is prose.

| section | holds | role |
| --- | --- | --- |
| `Goal` | the owner's intent, in detail; the title sums it up | goal |
| `Definition of done` | criteria, one per numbered or bulleted line | done |

## Waits

What an open issue waits on, first match:

1. an open issue the board lists as blocking it: `blocked by #<n>`;
2. its latest ask or answer is an ask: `waits on the owner` with audience `owner`, else `waits on the manager`;
3. holders with names: `held`;
4. a deferred reason that no later holders with names ended: `deferred`;
5. else `no holder`.
