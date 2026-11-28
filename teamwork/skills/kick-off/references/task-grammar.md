# Task grammar

How a teamwork task is written: its text is prose a person reads, and its data is fields [use-board.py](../scripts/use-board.py) takes as options, so no code reads data out of prose and no writer formats any. A write this grammar refuses posts nothing.

## Keywords

A comment's first line opens with one, which the verb that posts it writes from its option: `comment --blocked` or `--reported`, `decide --decision`, `edit --reason`, `resolve --summary`; a `--text` file that opens with a keyword is refused, naming the option its line belongs in.

| keyword | the comment | verb |
| --- | --- | --- |
| `BLOCKED` | asks a question; the asker waits on the answer | `comment` |
| `REPORTED` | informs: findings each citing its source, a batch landed with the root's words not all covered, or a close summary | `comment`, `resolve` |
| `DECIDED` | a decision, which binds until a newer one, or an event, which a verb posts to say what it set | `decide`; `hold`, `depend`, `edit` |

## Fields

A comment is kept as its kind (the keyword it opens with, a `DECIDED` a decision when it holds one, else an event), its keyword line, its text, its author, its time and the fields [board-record-schema.json](../assets/board-record-schema.json) names, which every write is checked against; a task keeps the tasks it waits on beside its title. A text never carries data: a write refuses, posting nothing, a text that holds a `teamwork` or `decision` fence.

| field | set by | meaning |
| --- | --- | --- |
| holders | `hold <task> --holders <names>`, `decide --holders` | the sessions that hold the task; none when empty |
| asks | `comment --asks owner` | the owner answers this `BLOCKED`, not the manager |
| options | `comment --option <answer>`, once per answer | the answers a `BLOCKED` offers, numbered from 1 in the order given; two or more on a question to the owner, who answers with a number |
| live runs | `decide --live-runs <n>` | how many live sessions the checks run in one worktree may start in all; 4 when none says |
| depends | `depend <task> --depends <numbers>`, `file --depends` | the tasks this one waits on; it waits until each is closed as completed |
| decision | `decide --decision <sentence>` | one binding sentence |
| by | `decide --by owner --owner-said <file>`, else the calling session | who decided: `owner`, the owner's words as they typed or picked them in the writing session quoted as `>` lines, else the writing session's own name |
| judge note | `decide --judge-note <file>` | the cases a judge tries against the task's criteria; a decision whose text names a judge note, in any spelling, is refused |
| supersedes | `decide --supersedes <url>` | the decision it replaces, anywhere in the same root's tree |
| answers | `decide --answers <url>` | the `BLOCKED` it settles, on the same task |

## Decisions

- **Binds**: a decision binds its task and that task's parts. A task's binding set, which `read` prints, is the decisions on it and on its ancestors that no decision in the root's tree supersedes, and none once the root is stopped.
- **Authority**: `decide` refuses a decision that supersedes one by the owner unless it is `--by owner` too.
- **Questions**: a `BLOCKED` is an open question until a later decision settles it: one with `--answers` settles each question whose url it names, a question to the owner only when the decision is `--by owner`, which `decide` refuses otherwise; one without `--answers` settles none. A `BLOCKED` with `--again <url>` repeats the question that url names: it joins that question and closes with it, so two questions with the same first line stay two.
- **Events**: a `DECIDED` with no decision field binds nothing: the note of a `hold`, a `depend`, a body edit or a stop. An old event whose only field is `answers` still settles the questions it names; no verb writes one now.

## Sections

A task's sections, each a `## <section>` heading in the body, which holds their current text; a comment's heading is prose.

| section | holds |
| --- | --- |
| `Goal` | the owner's intent, in detail, with its purpose and each guess marked `(guess)`, and, from task 1305, a `Path:` line naming the flow of the changed part ([check-criteria.py](../scripts/check-criteria.py) and the board writes `file` and `edit` of [use-board.py](../scripts/use-board.py) refuse a Goal without one); the title sums it up |
| `Definition of done` | criteria, one per numbered or bulleted line |

### Criteria

A criterion names the parts it checks by a `covers:` clause of backticked parts, each a path, a folder, or `<path>#<section>`: a Markdown heading's anchor, the lines up to the next heading as high, or an HTML element's `id`, its lines, so a task can name one section of a document. A criterion with no `covers:` covers every part, so any fix re-judges it; [run-criteria.py](../scripts/run-criteria.py) `--since <sha>` names the criteria a fix since the sha touched.

A `N. [task] #n <title>` line in `Definition of done` is a part, not a criterion: the task it names belongs to this one, its parent, and is met when that task is closed as completed. A task has one parent, and a task with none is a root. A task numbered at or above the cut-off, which [check-criteria.py](../scripts/check-criteria.py) `--cut-off` prints, holds at most 5 criteria, parts not counted; the lint learns a task's number by `--task <n>`, and with none applies the cut-off's rules, as for a task not yet filed. `file` and `edit` also refuse, writing nothing, each defect the lint prints on the new body, `edit` only those the stored body did not hold. `file`, `edit` and `depend` refuse, writing nothing, parts and waits that make a cycle or a second parent or name an unknown task.

## States

A task is open, completed or stopped; `use-board.py` changes a task's state only by the moves below, and any other `edit` or `reopen` leaves it as it was. A task completed by a move completes its parent too, once every part of the parent is completed and it holds no criterion.

| state | move | result |
| --- | --- | --- |
| none | `file` | open |
| open | `resolve`, every part completed | completed, and so is its parent once every part of the parent is completed and it holds no criterion |
| open | `resolve`, a part open or stopped | refused |
| open | `resolve --not-planned` | stopped, with each open part |
| completed or stopped | `resolve` | refused |
| completed or stopped | `reopen` | open, with each closed ancestor |
| completed or stopped | `edit` adding a part | open, with each closed ancestor |
| open | `edit` dropping a part or a criterion, a part left and every part left completed | completed, when it holds no criterion |

## Waits

What an open task waits on, first match:

1. an open question to the owner: `waits on the owner`, the one wait the pane highlights; the opened row numbers the answers each such question offers, under its question when two are open, and the owner answers the manager with a number;
2. a task it depends on that is not closed as completed: `blocked by #<n>`;
3. holders with names: `held`;
4. else `no holder`.

A question to the manager is no wait of the task's: it stays an open question, drawn dim, which the team clears.

## Rules

- **Read**: `read <task>` cuts each body edit's diff to one line unless `--full`; `read <task> --body` prints the stored body and nothing else, the file an `edit` starts from. `--as worker`, or a call from a worker's session without `--as judge`, leaves out each judge note, which names probes of a criterion's implementation, and ends with the related work [worker.md](worker.md)'s Define names; `--as judge` leaves out the open questions and each `BLOCKED:` comment, which are worker history.
- **Body**: written when the task is filed, in free Markdown; afterwards only its sections and its summary line change, and only by `edit`, which takes the whole new body, posts a comment holding the diff from the stored one, then stores it.
- **Summary line**: a root's body opens with one plain sentence that sums up the work, on one line. The sentence carries no label (`**Summary:**`) and no quote header (`Owner said, verbatim:`). The owner's words follow verbatim, then a `Why:` line of the purpose in the manager's words. Another task's title sums it up, so its `Goal` opens with no summary.
- **Plain words**: a title and a decision's sentence are what the task pane shows, and a summary line opens a root's body, so a reader who knows no task's history must read each at once: one idea, in everyday words, naming no task by its number and no term the owner did not use. A summary line or decision holds at most 20 words and one `,`, `;` or `:`, and a title at most 40 characters; the write path refuses one that breaks a cap, posting nothing. Put the detail, the numbers and the terms in the body or the comment around it.
- **Complete sentence**: each criterion opens with its name, `1. [check] **<name>**: <details>`, because the pane shows the name alone; the name is a complete sentence a reader understands without the task's history, such as `**The closed list shows the latest four tasks**`, not a label such as `Four closed`; the write path refuses, posting nothing, a name of fewer than 5 words or beyond the caps of Plain words.
- **Comment**: every later fact. Its first line opens with a keyword and a colon, then the kind of work it records in plain words after the keyword, `REPORTED: batch landed …`; the rest is free Markdown. A keyword says what the comment does to the task, never who spoke; name a source in the content, `owner said: …`.
- **Latest wins**: a later value of a field replaces an earlier one; no comment is edited or deleted.
