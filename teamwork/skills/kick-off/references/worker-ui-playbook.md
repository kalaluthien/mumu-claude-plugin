# UI

1. Change a fixture page or screen first, then what uses it.
2. Run the render check on each changed page or screen until it prints `ok`; a run over a few minutes goes to a subagent.
3. Look at each 390 px and 1200 px capture until it shows the change; past 3 pages, one read-only subagent per page.
4. A live pane (`teamwork/hooks/issue-pane.tsx`): list the owner's layout words (colors, spacing, symbols, format; their screenshots too) from the task and the issues it follows, and quote beside each the live row that meets it; the owner's word beats your taste, and an unclear word is a `BLOCKED:`.
5. A live pane, in a narrow width: no text is cut, hidden or shrunk; a link and a fold mark keep full width (`flexShrink={0}`), long text wraps, and each fold row presses over its whole text but the link.
