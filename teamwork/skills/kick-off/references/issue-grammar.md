# Issue grammar

How a teamwork issue is written: its text is prose a person reads, and its data is fields [use-board.py](../scripts/use-board.py) takes as options, so no code reads data out of prose and no writer formats any.

## Keywords

A comment's first line opens with one, which the verb that posts it sets or checks.

| keyword | the comment | verb |
| --- | --- | --- |
| `BLOCKED` | asks a question; the asker waits on the answer | `comment` |
| `REPORTED` | informs: findings each citing its source, a batch landed with the root's words not all covered, or a close summary | `comment`, `resolve` |
| `DECIDED` | a decision, which binds until a newer one, or an event, which a verb posts to say what it set | `decide`; `hold`, `depend`, `edit` |

## Fields

A comment is kept as its text and the fields [board-record-schema.json](../assets/board-record-schema.json) names, which every write is checked against; a task keeps the tasks it waits on beside its title. A text never carries data: a write refuses, posting nothing, a text that holds a `teamwork` or `decision` fence, which only records older than the fields hold and [legacy_records.py](../../../lib/legacy_records.py) still reads.

| field | set by | meaning |
| --- | --- | --- |
| holders | `hold <issue> <name>...`, `decide --holders` | the sessions that hold the task, replacing every earlier value; none when empty |
| asks | `comment --asks owner` | the owner answers this `BLOCKED`, not the manager |
| options | `comment --option <answer>`, once per answer | the answers a `BLOCKED` offers, numbered from 1 in the order given; two or more on a question to the owner, who answers with a number |
| live runs | `decide --live-runs <n>` | how many live sessions the checks run in one worktree may start in all, replacing every earlier value; 4 when none says |
| depends | `depend <issue> <n>...`, `file --depends` | the tasks this one waits on, replacing every earlier value; it waits until each is closed as completed |
| decision | `decide`, the text's first line | one binding sentence |
| by | `decide --by <who>`, else the calling session | who decided: `owner`, the owner's words quoted in the text as a `>` line or in double quotes, else a session's name |
| one-way | `decide --one-way` | the decision is hard to undo |
| supersedes | `decide --supersedes <url>` | the decision it replaces, anywhere in the same root's tree |
| answers | `decide --answers <url>` | the `BLOCKED` it settles, on the same task |

## Decisions

- **Binds**: a decision binds its task and that task's parts. A task's binding set, which `read` prints, is the decisions on it and on its ancestors that no decision in the root's tree supersedes, and none once the root is closed as not planned; a decision still waiting as **One-way** says supersedes nothing yet.
- **One-way**: a one-way decision by a worker, a session not named `owner` or `<project>-manager`, binds once a later decision on the same task by the manager or the owner repeats its sentence or supersedes it.
- **Authority**: `decide` refuses, posting nothing, a decision that supersedes one by the owner unless it is `--by owner` too.
- **Questions**: a `BLOCKED` is an open question until a later decision settles it: one with `--answers` settles the question it names and each earlier open ask with the same first line, since an ask posted again is one question; one without settles each open question its decider may answer, which is every one for the owner, those not asked of the owner for a manager, and none for a worker. A `DECIDED` posted before `2026-11-05` that is no event settles every one.
- **Events**: a `DECIDED` with no decision field binds nothing and answers nothing: the note of a `hold`, a `depend`, a body edit or a stop.

## Sections

A task's sections, each a `## <section>` heading in the body, which holds their current text; a comment's heading is prose.

| section | holds |
| --- | --- |
| `Goal` | the owner's intent, in detail, with its purpose and each guess marked `(guess)`, and, from task 1305, a `Path:` line naming the flow of the changed part ([check-criteria.py](../scripts/check-criteria.py) and the board writes `file` and `edit` of [use-board.py](../scripts/use-board.py) refuse a Goal without one); the title sums it up |
| `Definition of done` | criteria, one per numbered or bulleted line |

A `N. [task] #n <title>` line in `Definition of done` is a part, not a criterion: the task it names belongs to this one, its parent, and is met when that task is closed as completed. A task has one parent, and a task with none is a root. A task numbered at or above the cut-off, which [check-criteria.py](../scripts/check-criteria.py) `--cut-off` prints, holds at most 5 criteria, parts not counted; the lint learns a task's number by `--task <n>`, and with none applies the cut-off's rules, as for a task not yet filed. `file`, `edit` and `depend` refuse, writing nothing, parts and waits that make a cycle or a second parent or name an unknown issue.

## States

A task is open, completed or stopped; `use-board.py` changes a task's state only by the moves below, and any other `edit` or `reopen` leaves it as it was.

| state | move | result |
| --- | --- | --- |
| none | `file` | open |
| open | `resolve`, every part completed | completed, and so is its parent once every part of the parent is completed and it holds no criterion |
| open | `resolve`, a part open or stopped | refused |
| open | `resolve --not-planned` | stopped, with each open part |
| completed or stopped | `resolve` | refused |
| completed or stopped | `reopen` | open, with each closed ancestor |
| completed or stopped | `edit` adding a part | open, with each closed ancestor |
| open | `reopen` | open |
| open | `edit` dropping its last part | open |
| open | `edit` dropping a part or a criterion, a part left and every part left completed | completed, when it holds no criterion, and so is its parent once every part of the parent is completed and it holds no criterion |

## Waits

What an open issue waits on, first match:

1. an open question to the owner: `waits on the owner`, the one wait the pane highlights; the opened row numbers the answers each such question offers, under its question when two are open, and the owner answers the manager with a number;
2. a task it depends on that is not closed as completed: `blocked by #<n>`;
3. holders with names: `held`;
4. else `no holder`.

A question to the manager is no wait of the task's: it stays an open question, drawn dim, which the team clears.

## Rules

- **Read**: `read <issue>` prints a task's title, state, holders, labels, parent, the tasks it waits on, its body, the decisions that bind it, its open questions and its comments, each body edit's diff cut to one line unless `--full`. `--as worker` leaves out each `Judge note:` paragraph, which names probes of a criterion's implementation; `--as judge` leaves out the open questions and each `BLOCKED:` comment, which are worker history.
- **Body**: written when the issue is filed, in free Markdown; afterwards only its sections and its summary line change, and only by [edit-issue-body.py](../scripts/edit-issue-body.py), which first posts a comment holding the exact diff, then applies it.
- **Summary line**: a root's body opens with one plain sentence that sums up the work, on one line. The sentence carries no label (`**Summary:**`) and no quote header (`Owner said, verbatim:`). The owner's words follow verbatim, then a `Why:` line of the purpose in the manager's words. The owner's words change a root's scope often, so the manager rewrites the line and the title at each material change. Another task's title sums it up, so its `Goal` opens with no summary.
- **Plain words**: a title and a decision's sentence are what the issue pane shows, and a summary line opens a root's body, so a reader who knows no task's history must read each at once: one idea, in everyday words, naming no task by its number and no term the owner did not use. A summary line or decision holds at most 20 words and one `,`, `;` or `:`, and a title at most 40 characters; the write path refuses one that breaks a cap, posting nothing. Put the detail, the numbers and the terms in the body or the comment around it.
- **Complete sentence**: each criterion opens with its name, `1. [check] **<name>**: <details>`, because the pane shows the name alone; the name is a complete sentence a reader understands without the task's history, such as `**The closed list shows the latest four tasks**`, not a label such as `Four closed`; the write path refuses, posting nothing, a name of fewer than 5 words or beyond the caps of Plain words.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, then the kind of work it records in plain words after the keyword, `REPORTED: batch landed …`; the rest is free Markdown. A keyword says what the comment does to the issue, never who spoke; name a source in the content, `owner said: …`.
- **Trusted authors**: only a body or comment by an author the board adapter trusts records anything; code reads any other as prose, since anyone may comment on a public board.
- **Latest wins**: a later value of a field replaces an earlier one; no comment is edited or deleted.
