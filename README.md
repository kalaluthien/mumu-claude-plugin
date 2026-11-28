# mumu-claude-plugin: Claude Code plugins

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow)](https://buymeacoffee.com/kalaluthien)

Three Claude Code plugins for one person who runs several Claude sessions at once. Each works alone, so install only the ones you need. The skills start from plain words, so you rarely type a slash command.

The table below says what each plugin is for and gives one first thing to try.

| plugin | use it to | first thing to try |
| --- | --- | --- |
| **teamwork** | hand a job to Claude and get it back reviewed and merged | in a herdr tab: "Be this project's teamwork manager: fix the login timeout" |
| **paperwork** | explain a system, a process or requirements as a page you can browse | `/paperwork:system describe how the release pipeline works` |
| **homework** | stop Claude from repeating a mistake you already corrected | set a memory folder, correct a session, then say "keep this as a lesson" |

## Install

Type these lines inside a Claude Code session, for the plugins you want. Then run `/reload-plugins` once.

```
/plugin marketplace add kalaluthien/mumu-claude-plugin
/plugin install teamwork@mumu-claude-plugin
/plugin install paperwork@mumu-claude-plugin
/plugin install homework@mumu-claude-plugin
```

Every plugin needs Claude Code (`claude update` updates it) and Python 3.9 or later. Each plugin section below lists what it adds.

## Teamwork

Teamwork hands a job to Claude and returns it reviewed and merged. You make one session your project's manager and say what you want. It files the ask as a task and starts a worker session in a new tab. The worker builds the change in its own copy of the repository. A fresh reviewer checks the work, and nothing merges without its approval. You only answer questions.

**Needs**: Claude Code 2.1.299 or later; macOS; `git`; [herdr](https://herdr.dev), a terminal app that gives each session its own tab. Add GitHub's `gh` tool, signed in, only if your repository takes pull requests.

The words below name the parts of a team.

- **manager**: the one session per project that files tasks, starts workers and answers their questions. Its tab is `<project>-manager`.
- **task**: one unit of work, with a goal and checks that fail before the change and pass after it.
- **worker**: a session that builds one task in its own git worktree, a separate copy of the repository.
- **judge**: a fresh reviewer that runs the task's checks and answers `approve` or `fix`.
- **sentinel**: a light session for one duty that never ends, such as answering comments on a page.
- **board**: the tasks and their comments, kept in your repository's git under `refs/teamwork-blackboard`, never on GitHub.
- **`BLOCKED:` and `DECIDED:`**: a worker's question on a task, and the answer that binds every later session until a newer one replaces it.

The [authority table](teamwork/skills/kick-off/references/protocol.md#authority) lists what each role may decide alone.

### Before you start

1. Install herdr, then start it with `herdr` in your terminal.
2. Go to your repository's folder in a herdr tab and start `claude`. Restart a `claude` that began outside herdr.
3. Check that the repository has a commit on its main branch, since workers branch from it and merge back.

### First run

1. Type `Be this project's teamwork manager: fix the login timeout`, with your own ask after the colon.
2. Watch the manager file the task and start a worker. The Tasks pane opens beside the chat and lists the task.
3. Answer the manager when a worker needs you. Reply to a numbered question with the number alone, such as `2`.
4. Wait for a judge to approve the exact commit. The worker then merges into your main branch, or opens a GitHub pull request if your `AGENTS.md` or `CONTRIBUTING.md` says so. To hold a change back, tell the manager before the judge approves.
5. Read the manager's message that the task is done.

One task spends several sessions' worth of usage, since each worker and judge is a session of its own.

### What runs by itself

You call none of these. The [`kick-off` skill](teamwork/skills/kick-off/SKILL.md) plays every role. Ask the manager for a sentinel, or to hand over to a fresh manager when its context grows long.

| part | when it runs | what it does |
| --- | --- | --- |
| [`route-event.py`](teamwork/hooks/route-event.py) hook | a session starts | tells a manager, worker or sentinel its role and what waits on it |
| `route-event.py` hook | a team session runs a shell command | refuses a write to a GitHub issue and a worker's `cd` into your main checkout |
| `route-event.py` hook | a worker tries to stop | sends it back once while a task it holds is open |
| [`print-team-gaps.py`](teamwork/monitors/print-team-gaps.py), the `heartbeat` monitor | a manager has a worker, and in each worker | shows the manager where the board and the team disagree, and wakes a worker when its wait ends |
| Tasks pane `teamwork-tasks`, [`draw-task-pane.tsx`](teamwork/hooks/draw-task-pane.tsx) | a session becomes a manager | lists open tasks as a tree with a search box |

## Paperwork

Paperwork describes a subject, such as code, a process or requirements, so that a reader can rebuild it. It writes one **contract**: a data file (JSON) of the subject's parts and how they connect, its step-by-step scenarios, and each question no source answers, kept as a named **gap**. A checker refuses a contract that breaks its rules. A fresh reader then tests whether the subject can be rebuilt from the contract alone.

**Needs**: Claude Code 2.1.98 or later, and a browser to open its pages. It has no hooks and no monitors.

### First run

1. Start a session in the folder that holds your subject.
2. Type `/paperwork:system describe how <your subject> works`, or say the same in plain words.
3. Answer the questions the session asks where the sources do not settle a point.
4. Open the HTML page path it gives you in a browser. The page shows a diagram per level, a card for what is under the pointer, playable scenarios, and search (press `/`). A **level** is one zoom of the subject, small enough to read at once.
5. Ask the session to open the page for comments, to change it by commenting. It serves the page on `127.0.0.1` behind a random link, applies each comment you leave, and reloads. It serves a page only when you ask.

[A finished example page](paperwork/skills/system/examples/self/page.html) shows the result. Clone the repository, or save the file's raw view, and open it in a browser.

### Skills

- [`system`](paperwork/skills/system/SKILL.md): describes a system, a process or requirements. Its [relay playbook](paperwork/skills/system/references/relay.md) applies your comments or edits on a local page.
- [`flow`](paperwork/skills/flow/SKILL.md): draws calls between systems, or a plan of work, as sequence diagrams.

## Homework

Homework makes each session keep what it learned, a **lesson**, where the next session will read it. Claude Code keeps an auto-memory: note files a session reads before it acts, listed in a `MEMORY.md` index. Homework adds each lesson to that memory once, and cleans up older notes now and then.

**Needs**: Claude Code 2.1.224 or later; macOS or Linux; `git`; GitHub's `gh` tool, signed in; herdr, only for the memory clean-up below.

### First run

1. Make a shared memory folder with `mkdir -p ~/.claude/memory`.
2. Name it in `~/.claude/settings.json`, as one more key of the object already there:

   ```json
   { "autoMemoryDirectory": "~/.claude/memory" }
   ```

   Every project's sessions now read and write that folder, so copy in any older notes you want to keep. The memory scripts exit with a message naming this setting until you set it.
3. Correct a session and say "keep this as a lesson". It runs a **retro**: it reviews what went wrong, then files each lesson in the folder.
4. Or work as usual. When a session in a git repository stops after enough happened, a hook asks it for a retro with a line that starts `Wrap-up signal:`.
5. Read `~/.claude/memory/MEMORY.md` to see what was kept. Each situation is one file with its lessons under it.

### Dream: the memory clean-up

A **dream** needs 8 or more changed memory files, and also a repeated mistake or a work preference that is due. It backs memory up and reads recent sessions of every project on your machine. It then tidies every memory folder. Before it hands over a repeat, a preference or a fix that widens a permission or a guard, it asks you with numbered choices. The [dream playbook](homework/skills/wrap-up/references/dream.md) lists each step.

A session that cannot run workflows opens a separate Dreamer session in a new herdr tab. Outside herdr, it asks you to type the slash command yourself.

### What runs by itself

You call none of these.

| part | when it runs | what it does |
| --- | --- | --- |
| [`print-repository-memory.py`](homework/hooks/print-repository-memory.py) hook | a session starts | tells the session where lessons go, and shows the index of lessons true only in this repository |
| [`signal-wrap-up.py`](homework/hooks/signal-wrap-up.py) hook | a session in a git repository stops | asks for a retro after enough failed or total tool calls, or at the session's 25th call, and counts changed memory files |
| [`homework:dreaming-workflow`](homework/workflows/dreaming-workflow.js) | a dream starts | maps recent sessions, digs into the most repeated mistakes and your preferences, and tidies every memory folder |

### What gets written where

- **A lesson true in every project**: the shared memory folder.
- **A lesson wrong or harmful outside one repository**: `<memory folder>/<repo>/`, where `<repo>` is the origin's name, else the checkout's folder name.
- **A lesson about a skill**: memory, marked `skill:`, until a dream asks what to do with it.
- **A fix to a hook, script or instruction file**: the project's own repository, landed the way that project takes changes. A repository that is not yours gets a patch for you to apply.
- **History of every retro and dream**: `~/.claude/memory.git`, a bare git directory beside the folder. `git --git-dir ~/.claude/memory.git log -p` shows each change. It keeps a credential once written, so delete it to purge one.
- **Dream digests**: the plugin's data folder, readable by you alone, with key-like strings of GitHub, Anthropic, OpenAI, Slack and AWS masked.

Move a memory file between the two memory folders with `homework/skills/wrap-up/scripts/move-memory.py <file> <folder>`.

### Turn the ask off

Set `HOMEWORK_WRAP_UP=off` in the environment Claude Code starts with, or in a repository's `.claude/settings.local.json`, merged into the object already there:

```json
{ "env": { "HOMEWORK_WRAP_UP": "off" } }
```

The hook then neither asks nor writes. You can still ask for a retro.

## Contribute

- [AGENTS.md](AGENTS.md) holds the rules every plugin follows, from [Plugin layout](AGENTS.md#plugin-layout) on.
- [CONTRIBUTING.md](CONTRIBUTING.md) says how to report a problem, ask a question or run a local clone.

## License

[Apache-2.0](LICENSE); third-party works are named in [NOTICE](NOTICE). This project is not affiliated with Anthropic.
