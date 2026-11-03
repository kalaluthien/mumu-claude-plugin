# Issue grammar

How a teamwork issue is written, so a person reads it as prose and code composes its state from it. [issue_state.py](../../../lib/issue_state.py) loads the tables below; a keyword or key exists only here, and code names only a row's role.

## Keywords

| keyword | the comment | role |
| --- | --- | --- |
| `BLOCKED` | asks a question with its options; the asker waits on the answer | ask |
| `DECIDED` | binds until a newer one: answers, routes, orders, or adds intent, its source named and its words quoted | answer |
| `REPORTED` | informs: findings each citing its source, a batch landed with the root's words not all covered, or a close summary; open or closed is the board's state | |

## Data

Data a script reads sits only in a fenced block whose info string is `teamwork`, one `key: value` per line; explanation never uses that fence, so prose never parses as data. Only lines inside such a fence count, in a body or any comment, each value as written, so a `holders:` line outside it, or a name in brackets (`[a-worker]`), holds nothing and the heartbeat routes the issue again.

````markdown
DECIDED: issue-pane-worker holds this.

```teamwork
holders: issue-pane-worker
```
````

| key | value | role |
| --- | --- | --- |
| `holders` | session names, space-separated, replacing every earlier value; empty when no one holds it | holders |
| `cloud` | the holders that run as cloud sessions, space-separated, replacing every earlier value, since no local listing shows them; a name counts as live on every open issue | cloud |
| `asks` | `owner` on an ask the owner answers, not the manager | audience |
| `depends on` | the tasks this one waits on, `#a #b`, read from the body only; a task waits until each is closed as completed | depends |

## Decisions

A decision is a `DECIDED` comment holding a fenced block whose info string is `decision`, written by `use-board.py decide` on the task it binds, one `key: value` per line:

| key | value | role |
| --- | --- | --- |
| `decision` | one binding sentence | decision |
| `decided by` | `owner`, the owner's words quoted in the comment as a `>` line or in double quotes, else the deciding session's name | decider |
| `door` | `one-way` or `two-way` | door |
| `supersedes` | the url of the decision it replaces, anywhere in the same root's tree | supersedes |
| `answers` | the url of the `BLOCKED` it settles | answers |
| `depends on` | the tasks it waits on, `#a #b` | depends |

- **Binds**: a decision binds its task and that task's parts. A task's binding set is the decisions on it and on its ancestors that no decision in the root's tree supersedes, and none once the root is closed as not planned; a decision still waiting on its door supersedes nothing yet.
- **Door**: a `one-way` decision by a worker, a session not named `owner` or `<project>-manager`, binds once a later decision on the same task by the manager or the owner repeats its `decision` or supersedes it.
- **Authority**: `decide` refuses, posting nothing, a decision that supersedes one `decided by: owner` unless it is `decided by: owner` too; `comment` refuses any decision block, so each one passes this check.
- **Questions**: a `BLOCKED` is an open question until a decision names its url in `answers`. A `BLOCKED` posted before `2026-11-05` also closes on a later `DECIDED` that is no event.
- **Events**: a `DECIDED` with no `decision` block is an event when it carries a `teamwork` block or a body edit's `diff`, or is the note a stop posts on the stopped parent; it binds nothing and answers nothing. Any other `DECIDED` with no block, posted since that date, is a decision the index cannot read, which the heartbeat lists.

## Sections

A task's sections, each a `## <section>` heading in the body, which holds their current text; a comment's heading is prose.

| section | holds | role |
| --- | --- | --- |
| `Goal` | the owner's intent, in detail; the title sums it up | goal |
| `Definition of done` | criteria, one per numbered or bulleted line | done |

A `N. [task] #n <title>` line in `Definition of done` is a part, not a criterion: the task it names belongs to this one, its parent, and is met when that task is closed as completed. A task has one parent, and a task with none is a root. A task numbered at or above the cut-off, which [check-criteria.py](../scripts/check-criteria.py) `--cut-off` prints, holds at most 5 criteria, parts not counted; the lint learns a task's number by `--task <n>`, and with none applies the cut-off's rules, as for a task not yet filed.

## Waits

What an open issue waits on, first match:

1. a task its `depends on` names that is not closed as completed: `blocked by #<n>`;
2. an open question: `waits on the owner` when the latest one's audience is `owner`, else `waits on the manager`;
3. holders with names: `held`;
4. else `no holder`.

## Rules

- **Body**: written when the issue is filed, in free Markdown; afterwards only its sections and its summary line change, and only by [edit-issue-body.py](../scripts/edit-issue-body.py), which first posts a comment holding the exact diff, then applies it.
- **Summary line**: a root's body opens with one plain sentence that sums up the work, on one line, because the issue pane shows the body's first paragraph and nothing when it starts with `#`. The sentence carries no label (`**Summary:**`) and no quote header (`Owner said, verbatim:`). The owner's words and the rest follow. The owner's words change a root's scope often, so the manager rewrites the line and the title at each material change. Another task's title sums it up, so its `Goal` opens with no summary; each criterion opens with its name, `1. [check] **<name>**: <details>`, because the pane shows the title and the names and folds the rest.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, then the kind of work it records in plain words after the keyword, `REPORTED: batch landed …`; the rest is free Markdown. A keyword says what the comment does to the issue, never who spoke; name a source in the content, `owner said: …`.
- **Fewest keywords**: a kind of work gets a keyword of its own only when code must tell it apart or its category differs wholly; comments posted under words no longer listed stay as written, read as prose.
- **Trusted authors**: only a body or comment by an author the board adapter trusts records anything; code reads any other as prose, since anyone may comment on a public board.
- **Latest wins**: a later record replaces an earlier one of the same role; no comment is edited or deleted.
