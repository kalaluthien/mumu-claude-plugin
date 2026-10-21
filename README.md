# mumu-claude-plugin: three Claude Code plugins

Three Claude Code plugins that let one person run a small team of Claude sessions without losing the plot: **teamwork** turns what you ask for into reviewed, merged work; **paperwork** shows you things as pages and settles open questions; **homework** makes sure each session leaves behind what it learned.

Each plugin works alone.

## Installation

Add this repository as a marketplace, then install the plugins you want:

```
/plugin marketplace add kalaluthien/mumu-claude-plugin
/plugin install teamwork@mumu-claude-plugin
/plugin install paperwork@mumu-claude-plugin
/plugin install homework@mumu-claude-plugin
```

What each one needs on your machine:

| plugin | needs |
| --- | --- |
| teamwork | [`gh`](https://cli.github.com/), signed in; [herdr](https://herdr.dev), the terminal workspace where sessions live and talk by name |
| paperwork | Python 3 with [`uv`](https://docs.astral.sh/uv/); Google Chrome for checking pages and diagrams; Java, only for the optional Alloy proofs |
| homework | nothing beyond Claude Code |

### Installation from a local clone

A clone makes a merged change reach your sessions after a `git pull`, with no reinstall.

1. Clone the repository:

   ```
   git clone https://github.com/kalaluthien/mumu-claude-plugin ~/workspace/plugins
   ```

2. Add the clone as a marketplace, in `~/.claude/settings.json`:

   ```json
   {
     "extraKnownMarketplaces": {
       "mumu-claude-plugin": {
         "source": { "source": "directory", "path": "/Users/<you>/workspace/plugins" }
       }
     }
   }
   ```

3. Enable the plugins per project, in the project's git-ignored `.claude/settings.local.json`:

   ```json
   {
     "enabledPlugins": {
       "teamwork@mumu-claude-plugin": true,
       "homework@mumu-claude-plugin": true,
       "paperwork@mumu-claude-plugin": true
     }
   }
   ```

## teamwork: the path from a request to a merged change

Three roles, each with a narrow job ([the authority table](teamwork/skills/kick-off/SKILL.md)):

- The **manager**, one per project, reads what you ask for, writes it down as a rough `backlog` issue and hands it to a worker. It decides who does what and in which order, and answers workers' questions. It never plans tasks or edits code.
- A **worker** owns a piece of work from start to finish. It splits the backlog into tasks, each with a goal and checks that fail today, builds them in its own git worktree, and spreads the effort over subagents.
- A **judge** is a fresh subagent that did not write the change. It reads the tasks or the diff and replies `approve <sha>` or `fix`. Nothing merges without an approval of the exact commit.

GitHub issues are the shared memory: a `BLOCKED:` comment is a question, a `DECIDED:` comment is the answer, and both outlive any session. Pull request policy belongs to each repository, not to the plugin.

The [`kick-off`](teamwork/skills/kick-off/SKILL.md) skill routes a session to the manager playbook ([manager](teamwork/skills/kick-off/references/manager.md)) or the worker playbook ([worker](teamwork/skills/kick-off/references/worker.md)), and a worker opens one more by the kind of work:

| worker playbook | when the work |
| --- | --- |
| [rules](teamwork/skills/kick-off/references/worker-rules-playbook.md) | changes skills, playbooks, rubrics, `AGENTS.md` or prompts |
| [code](teamwork/skills/kick-off/references/worker-code-playbook.md) | changes scripts, hooks, monitors, apps or services |
| [ui](teamwork/skills/kick-off/references/worker-ui-playbook.md) | changes a rendered page, diagram, screen or live pane |
| [migration](teamwork/skills/kick-off/references/worker-migration-playbook.md) | moves files, code or data to a new form with behaviour kept |
| [research](teamwork/skills/kick-off/references/worker-research-playbook.md) | ends in a report comment, not a change |

**Use it.** In a herdr workspace, start a session and ask it to manage:

```
Be this project's teamwork manager: fix the login timeout
```

That session becomes the manager. It files the backlog, starts a worker in a new tab, and from then on you mostly answer questions.

- A hook ([`route-event.py`](teamwork/hooks/route-event.py)) tells each session at start what waits on it, and keeps a worker from going idle while an issue it holds is open.
- A monitor ([`print-team-gaps.py`](teamwork/monitors/print-team-gaps.py)) tells the manager where GitHub and the team disagree, and wakes a worker when its wait ends.
- `/teamwork:issues` shows the Issues pane, a board of the open issues, again after you close it.

## paperwork: one checked model of a system

One Schema document holds what a system is, or must be, and every view is drawn from it after a checker passes it.

- [`/paperwork:zoom`](paperwork/skills/zoom/SKILL.md) models a system as a checked Schema document, then proves or shows it. Its playbooks:

  | playbook | runs when you ask to |
  | --- | --- |
  | [interpret](paperwork/skills/zoom/references/playbook/interpret.md) | model an existing system from its code, docs, configs or process |
  | [requirements](paperwork/skills/zoom/references/playbook/requirements.md) | model a system not yet built from requirements, a PRD or an intent |
  | [improve](paperwork/skills/zoom/references/playbook/improve.md) | improve or simplify a document by stated criteria |
  | [prove](paperwork/skills/zoom/references/playbook/prove.md) | prove a document's rules with Alloy (needs Java), or ask whether a run can break one |
  | [mermaid](paperwork/skills/zoom/references/ui/mermaid.md) | show a document in chat, the default |
  | [html](paperwork/skills/zoom/references/ui/html.md) | show a document as a clickable page that zooms level by level and plays scenarios |
  | [pele](paperwork/skills/zoom/references/ui/pele.md) | show one level as a restylable SVG or PNG |
  | [tldraw](paperwork/skills/zoom/references/ui/tldraw.md) | show a document on a tldraw canvas |

- [`/paperwork:litmus`](paperwork/skills/litmus/SKILL.md) turns a task into a grading spec for a judge, a benchmark or a human grading sheet. Its playbooks:

  | playbook | runs when you ask to |
  | --- | --- |
  | [author](paperwork/skills/litmus/references/playbook/author.md) | write a rubric, reward spec or grading spec from a task |
  | [calibrate](paperwork/skills/litmus/references/playbook/calibrate.md) | measure how far the judge agrees with itself or with people |
  | [grade](paperwork/skills/litmus/references/playbook/grade.md) | apply a spec to verdicts: rewards, a comparison of systems, a sheet people fill in |
  | [repair](paperwork/skills/litmus/references/playbook/repair.md) | fix a spec that ranked answers wrongly |

**Use it.**

```
/paperwork:zoom map how the release pipeline works
/paperwork:zoom prove that two workers never hold the same worktree
```

## homework: lessons kept across sessions

Keeps what a session learned, once, where the next reader will look.

- A Stop hook ([`wrap-up-signal.py`](homework/hooks/wrap-up-signal.py)) counts new lessons in the transcript, changed memory files, and whether the repository has a known way to run and verify itself. When a count crosses its line, it sends a one-line wrap-up signal.
- The [`wrap-up`](homework/skills/wrap-up/SKILL.md) skill acts on the signal, or on your ask, through one playbook per case:

  | playbook | runs when |
  | --- | --- |
  | [retro](homework/skills/wrap-up/references/retro.md) | enough lessons piled up, the session's first retro is due, you ask to keep a lesson, or nothing else fits |
  | [run-recipe](homework/skills/wrap-up/references/run-recipe.md) | the repository has no known way to run and verify itself, or the known way fails |
  | [dream](homework/skills/wrap-up/references/dream-how.md) | enough memory files changed, or you ask to tidy memory |
  | [dejavu](homework/skills/wrap-up/references/dejavu.md) | a recurring-pattern pass is due, or you ask for it |
  | [skill-authoring](homework/skills/wrap-up/references/skill-authoring.md) | you write or edit a skill or an agent file |
  | [hook-authoring](homework/skills/wrap-up/references/hook-authoring.md) | you write or edit a hook or a script |

- Every memory file says when it applies and when it would be wrong, so a stale lesson can be spotted.

**Use it.** The signal arrives on its own, and the skill is not in the slash menu. To ask for it yourself, tell Claude to keep a lesson (retro) or tidy memory (dream). It asks you nothing and reports what it did.

## Contribution to this repository

- [AGENTS.md](AGENTS.md) holds the rules every plugin follows: folder layout, how skills are written, how a design is split, how a change is evaluated.
- [CONTRIBUTING.md](CONTRIBUTING.md) says how to propose a change from a fork.
- Sessions load the plugins straight from a checkout, so a merged change reaches them after a pull and, for a `SKILL.md` or a hook, a `/reload-plugins`.
