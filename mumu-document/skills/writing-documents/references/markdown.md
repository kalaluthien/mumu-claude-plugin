# Markdown: GitHub or repository page

A GitHub issue, pull request or comment goes by the repository's procedure,
else `gh issue create`; a repository page (a README, `docs/`) is linked from
the README and lands by a branch and a pull request. The moves are headings;
each widget is its markdown column in the mapping. No Mermaid: an SVG reads
the same on every client.

## Body form

Unless the repository's procedure sets the form, a GitHub body is:

1. one sentence on why the change exists;
2. the figure of what the change alters;
3. the proof: each check run and its result;
4. the files in reading order, each with its why; files with nothing to say
   share one closing line, and a misleading `+`/`-` count is called out.

A `path:line` links to the blob at the head sha on GitHub, and is a relative
link on a repository page, so it follows the branch it is read on.

## Figures

1. Draw the figure as its widget on a page, by [artifact.md](artifact.md)'s
   Composition; its labels may stay English, since the page is not published.
2. Export it: `"${CLAUDE_PLUGIN_ROOT}/scripts/page/svg-export.py" <page>
   <dir>` writes `<dir>/<page>-<n>.svg`, one per figure, styles inlined.
3. On GitHub, reference it as `![<what it shows>](./<page>-<n>.svg)` and pass
   `--attach './<page>-<n>.svg#<what it shows>'` to `gh pr|issue
   create|edit|comment`, which uploads it and rewrites the reference; every
   later `--body-file` edit re-passes `--attach` for each figure, or the path
   stays local. On a repository page, commit it beside the page, its alt one
   sentence.
