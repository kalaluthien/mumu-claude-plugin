# GitHub issue or pull request

The body or a comment by the repository's procedure, else `gh issue create`.

## Body form

Unless that procedure sets the form:

1. one sentence on why the change exists;
2. the figure of what the change alters, as an attached SVG;
3. the proof: each check run and its result;
4. the files in reading order, each with its why; files with nothing to say
   share one closing line, and a misleading `+`/`-` count is called out;
5. each `path:line` a link to the blob at the head sha.

The moves are headings; each widget is its markdown column in the mapping.
No Mermaid: an SVG reads the same on every client.

## Figures

1. Draw the figure as its widget on a page, by [artifact.md](artifact.md)'s
   Composition; its labels may stay English here, since the page is not
   published.
2. Export it: `"${CLAUDE_PLUGIN_ROOT}/scripts/figure/svg-export.py" <page>
   <dir>` writes `<dir>/<page>-<n>.svg`, one per figure, with the styles
   inlined and the page's background behind them.
3. Reference it in the body as `![<what it shows>](./<page>-<n>.svg)` and
   attach it: `gh pr|issue create|edit|comment … --body-file <body> --attach
   './<page>-<n>.svg#<what it shows>'`; gh uploads the file and rewrites the
   reference to its url.
