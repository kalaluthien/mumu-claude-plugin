---
name: show-me
description: Use when the user wants to see something as a page instead of prose - where things stand or what changed, how a system works, what happens when you try, or which option to take.
disable-model-invocation: true
---

# show-me

**Seen or not done**: prose describing a picture, or a file path, is not showing it. Show the topic named, else the conversation's.

## Playbooks

Each playbook answers one reader question; read each one you place before building.

- **Where does it stand, what happened, what changed or is planned?** status, trend, incident, pull request, diff or draft under review, plan ahead: [references/sitrep/sitrep.md](references/sitrep/sitrep.md)
- **How does it work, or how should it?** a system, process, protocol or concept, or two compared; a design for one not yet built: [references/zoom-diagram/zoom-diagram.md](references/zoom-diagram/zoom-diagram.md)
- **What happens if I try?** a value judged by seeing it (colour, timing, prompt, config), a concept to play with, steps to follow: [references/interactive-demo/interactive-demo.md](references/interactive-demo/interactive-demo.md)
- **Which one?** named alternatives (approaches, designs, layouts, tools), ways to improve a system, or a verdict: merge, approve, keep, revert: [references/option-cards/option-cards.md](references/option-cards/option-cards.md)

An answer fitting one screen as a table or short fenced tree needs no page: give it in chat.

## Placing

- **One per question**: split the ask into the reader's questions, one playbook each, in this order: sitrep (what happened or changed), zoom-diagram (why, how it works), interactive-demo (what if I try), option-cards (what to do, which, is it ready). A change or draft review shows notes (sitrep) then ends in the verdict (option-cards); a failure or incident shows what happened (sitrep) before why (zoom-diagram).
- **drill-it first**: before building, run `drill-it` once with the settled ask, the placed playbooks' names in order (`sitrep`, `option-cards`, ...) as purposes, and each one's Parts (zoom diagram: its plan); build only from what it hands back.
- **Assembled**: page playbooks write fragments; `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/assemble-page.py" <plan.json> <out.html>` builds the page (usage lists the plan's fields). A zoom diagram's part comes from its playbook's `make-diagram.py part`.

## Delivery

**Delivery follows the ask**: an Artifact (`Artifact` tool) when the ask names one or one is in progress; the existing html page the ask names, in its own style; else a temporary HTML file in the scratchpad, sent with `SendUserFile`. Never open a local file in the user's browser.

## Constraints

- **Page parts**: a part is a fragment of the Parts its playbook names (`assemble-page.py` adds CSS and script); every table sits in a `.scroll` box. The page opens with the one-sentence answer and closes with the reader's next action; a `.reply` box, which a button's `data-reply` may fill, holds what the reader copies back to you.
- **Only what it needs**: no section, widget or control the answer does not use; cut facts that do not change the reader's view and repeated parts.
- **Counted as shown**: a stated count counts what the page shows.
- **One language**: the user's instructed language, else the ask's; a zoom diagram keeps terms in English per its `view-writing.md`.
- **Asking**: the zoom diagram's Interview and drill-it's Undecided go as rounds of the `grill-me` skill (its Asking a round and Settling); recommended options Settling takes stay off the page.

## Done when

1. `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/check-page.py" <page> --shots <dir>` prints `ok` last and you looked at both captures: the first screen answers the ask, every part reads at 1200 px, the text agrees with it. A zoom part also passes its playbook's Verification.
2. The page went out as Delivery says; chat gives the one-sentence answer and next action only.
