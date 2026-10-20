# mumu-claude-plugin

Three Claude Code plugins that let one person run a small team of Claude sessions without losing the plot: **teamwork** turns what you ask for into reviewed, merged work; **paperwork** shows you things as pages and settles open questions; **homework** makes sure each session leaves behind what it learned.

They were built by one owner for daily use, then rebuilt from scratch in October 2026 with a single brief: keep half the files, half the lines and half the concepts. What survived is small on purpose, and every plugin is built from the same three parts: hooks that act at fixed moments, monitors that watch in the background, and skills that hold the instructions, each working without knowing the others' insides. If something here looks missing, it was probably cut.

## Install

Add this repository as a marketplace, then install the plugins you want:

```
/plugin marketplace add kalaluthien/mumu-claude-plugin
/plugin install teamwork@mumu-claude-plugin
/plugin install paperwork@mumu-claude-plugin
/plugin install homework@mumu-claude-plugin
```

What each one expects on your machine:

| plugin | needs |
| --- | --- |
| teamwork | [`gh`](https://cli.github.com/), signed in; [herdr](https://herdr.dev), the terminal workspace where sessions live and talk by name |
| paperwork | Python 3 with [`uv`](https://docs.astral.sh/uv/); Google Chrome for checking pages and diagrams; Java, only for the optional Alloy proofs |
| homework | nothing beyond Claude Code |

## teamwork: from a request to a merged change

**The problem.** One Claude session doing everything forgets, wanders and grades its own homework. Many sessions with no structure step on each other.

**The idea.** Three roles, each with a narrow job ([the authority table](teamwork/skills/kick-off/SKILL.md)):

- The **manager**, one per project, reads what you ask for, writes it down as a rough `backlog` issue and hands it to a worker. It decides who does what and in which order, and answers workers' questions. It never plans tasks or edits code, so it stays cheap and quick.
- A **worker** owns a piece of work from start to finish. It splits the backlog into tasks, each with a goal and checks that fail today, builds them in its own git worktree, and spreads the effort over subagents.
- A **judge** is a fresh subagent that did not write the change. It reads the tasks or the diff and replies `approve <sha>` or `fix`. Nothing merges without an approval of the exact commit.

GitHub issues are the shared memory: a `BLOCKED:` comment is a question, a `DECIDED:` comment is the answer, and both outlive any session. Pull request policy belongs to each repository, not to the plugin.

**Using it.** In a herdr workspace, start a session and ask it to manage:

```
Be this project's teamwork manager: fix the login timeout
```

That session becomes the manager. It files the backlog, starts a worker in a new tab, and from then on you mostly answer questions. Under the hood, one hook ([`route-event.py`](teamwork/hooks/route-event.py)) tells each session at start what is waiting on it, and stops a worker from going idle while an issue it holds is still open, and a monitor ([`print-team-gaps.py`](teamwork/monitors/print-team-gaps.py)) tells the manager where GitHub and the team disagree and wakes a worker when its wait ends.

## paperwork: one checked model of a system

**The problem.** A system described in prose drifts: the words, the diagram and the rules each say something slightly different, and nobody checks that the rules hold.

**The idea.** One Schema document holds what a system is, or must be, and every view is drawn from it after a checker passes it.

- [`/paperwork:zoom`](paperwork/skills/zoom/SKILL.md) models a system as a checked Schema document: from its code (interpret), from requirements, or by improving an existing one. It proves the document's rules with Alloy when Java is around, and shows it as Mermaid in chat or as a clickable HTML page that zooms level by level and plays scenarios.
- [`/paperwork:litmus`](paperwork/skills/litmus/SKILL.md) turns a task into a grading spec for a judge, a benchmark or a human grading sheet, and measures, applies or repairs one.

**Using it.**

```
/paperwork:zoom map how the release pipeline works
/paperwork:zoom prove that two workers never hold the same worktree
```

## homework: lessons that stick

**The problem.** A session learns something the hard way, then ends, and the next session learns it again.

**The idea.** Keep what was learned, once, where the next reader will look. A Stop hook ([`wrap-up-signal.py`](homework/hooks/wrap-up-signal.py)) counts mechanically: new lessons in the transcript, memory files changed, whether the repository has a known way to run and verify itself. When a count crosses its line, it sends a one-line wrap-up signal, and the [`wrap-up`](homework/skills/wrap-up/SKILL.md) skill acts on it: it writes the lesson down, tidies memory that has grown messy, or records how to run the project. Every memory file says when it applies and when it would be wrong, so a stale lesson can be spotted.

**Using it.** You do not call it: the signal arrives on its own, and the skill is not in the slash menu. Ask Claude in words to keep a lesson (retro) or tidy memory (dream). It asks you nothing; it reports what it did.

## Working on this repository

Read [AGENTS.md](AGENTS.md) first. It holds the rules every plugin follows: the folder layout, how skills are written, how a design is split, and how a change to an agent system is evaluated. Its spirit fits in one line: every line has to change what the reader does next, or it goes.

Sessions load the plugins straight from a checkout, so a merged change reaches them after a pull and, for a `SKILL.md` or a hook, a `/reload-plugins`.
