---
name: zoom
description: Use when a system, a change or requirements must be modelled as a checked Schema document, proved with Alloy ("prove this invariant", "can this race happen"), or shown as a clickable HTML page.
---

# zoom

Turn what a system is, or must be, into one checked Schema document, then prove or show it. Read only the rows the ask needs, in order; each playbook reads `references/schema/` once, in its `## Domain` section.

## Route

| ask | playbook |
| --- | --- |
| model a system from its code, docs, configs or process, or from requirements, a PRD or an intent | [references/model.md](references/model.md) |
| prove a document's rules, or ask whether a run can break one (Alloy) | [references/prove.md](references/prove.md) |
| show a document as a clickable HTML page that zooms and plays scenarios | [references/show.md](references/show.md), then [references/ui/formats.md](references/ui/formats.md) |

An ask that names a document to show or prove reads that document and no playbook that writes one. Worked documents are in `examples/<name>/schema.json`, with `view.json` for the HTML page.

## Rules

- **Checked document**: run `${CLAUDE_PLUGIN_ROOT}/skills/zoom/references/schema/scripts/check-schema.py check doc.json` after each change; a document is handed over only when it prints `ok`.
- **Command paths**: a playbook's command paths are relative to its file.
- **One document**: the document is the one source; a renderer or a prover reads it and never changes it.
