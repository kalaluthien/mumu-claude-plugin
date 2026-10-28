---
name: zoom
description: Use when a system, a change or requirements must be modelled as a checked Schema document, improved, proved with Alloy ("prove this invariant", "can this race happen"), or shown as a diagram (Mermaid in chat, or a clickable HTML page).
---

# zoom

Turn what a system is, or must be, into one checked Schema document, then prove or show it. Read only the rows the ask needs, in order; each playbook reads `references/schema/` once, in its `## Domain` section.

## Route

| ask | playbook |
| --- | --- |
| model an existing system from its code, docs, configs or process | [references/interpret.md](references/interpret.md) |
| model a system not yet built from requirements, a PRD or an intent | [references/requirements.md](references/requirements.md) |
| improve or simplify an existing Schema document by stated criteria | [references/improve.md](references/improve.md) |
| prove a document's rules, or ask whether a run can break one (Alloy) | [references/prove.md](references/prove.md) |
| recheck a document read from code after the code changed | [references/recheck.md](references/recheck.md) |
| show a document in chat: the default renderer | [references/ui/mermaid.md](references/ui/mermaid.md), then [references/ui/formats.md](references/ui/formats.md) |
| show a document as a clickable HTML page that zooms and plays scenarios | [references/ui/html.md](references/ui/html.md), then [references/ui/formats.md](references/ui/formats.md) |
| show one level as a restylable SVG or PNG | [references/ui/pele.md](references/ui/pele.md) |

An ask that names a document to show or prove reads that document and no playbook that writes one. Worked documents are in `examples/<name>/schema.json`, with `view.json` for the HTML page.

## Rules

- **Checked document**: run `${CLAUDE_PLUGIN_ROOT}/skills/zoom/references/schema/scripts/check-schema.py check doc.json` after each change; a document is handed over only when it prints `ok`.
- **Command paths**: a playbook's command paths are relative to its file.
- **One document**: the document is the one source; a renderer or a prover reads it and never changes it.
