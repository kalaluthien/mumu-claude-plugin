# Plugin layout

A file in any plugin sits where [Anthropic's standard layout](https://code.claude.com/docs/en/plugins-reference#standard-layout)
and this table say. A script is named in lowercase words joined by `-` for
what it does or prints, never a verdict, state or measurement, with its
language extension.

| file | place |
| --- | --- |
| command a document, `~/.claude/settings.json` or another plugin names bare | `bin/<name>`, on the Bash tool's `PATH` |
| what two or more skills share | `lib/`: a module scripts import as `<noun>.py`, each doing one thing, and a document as `<noun>.md`; a script imports no other script |
| hook, monitor or CI command, or a script two skills run | `scripts/<name>.py`, run from `hooks/hooks.json` or `monitors/monitors.json` through `${CLAUDE_PLUGIN_ROOT}/scripts/` |
| a skill's own files | `skills/<skill>/`: `SKILL.md` and only `references/` (documents it loads), `scripts/` (code only it runs) and `assets/` (files it copies) |
| test | `tests/test_<name>.py`, named after the file or folder it checks, `-` as `_` |
| eval case | `evals/<case>/prompt.md` and `graders/<check>.md`, no `case.yaml` |

At a plugin's root sit only folders the harness or several skills use, never
a loose document.

## Paths

- A `SKILL.md` names a path a command runs, or a file outside the skill's
  folder, as `${CLAUDE_PLUGIN_ROOT}/<path>`, substituted when the skill loads,
  since a command runs from any directory.
- A link into the skill's own folder, such as `[lesson.md](references/lesson.md)`,
  stays relative, and so does every link from a file opened with Read, which
  is read verbatim with nothing substituted: relative to that file.
