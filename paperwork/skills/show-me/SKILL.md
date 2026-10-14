---
name: show-me
description: Use when the user wants to see something as a page instead of prose - where things stand or what changed, how a system works, what happens when you try, or which option to take.
disable-model-invocation: true
---

# show-me

**Seen or not done**: describing a picture in prose, or naming a file path, is not showing it. Show the topic named, else the conversation's.

## Playbooks

Each playbook answers one question the reader asks, and holds parts the page uses as needed. Read the playbook of each one you place before building.

| the reader asks | playbook |
| --- | --- |
| where does it stand, what happened, what changed or is planned? status, a trend, an incident, a pull request, a diff or a draft under review, a plan ahead | [references/sitrep/sitrep.md](references/sitrep/sitrep.md) |
| how does it work? a system, a process, a protocol, a concept, or two of them compared to understand them | [references/zoom-diagram/zoom-diagram.md](references/zoom-diagram/zoom-diagram.md) |
| what happens if I try? a value judged by seeing it (a colour, a timing, a prompt, a config), a concept to play with, steps to follow | [references/interactive-demo/interactive-demo.md](references/interactive-demo/interactive-demo.md) |
| which one? named alternatives (approaches, designs, layouts, tools), or a verdict to give: merge, approve, keep, revert | [references/option-cards/option-cards.md](references/option-cards/option-cards.md) |

An answer that fits on one screen as a table or a short fenced tree needs no page: give it in chat.

## Placing

- **One per question**: split the ask into the questions the reader puts and place the playbook of each, no other: what happened or what changed is sitrep; why, or how it works, is zoom-diagram; what happens if I try is interactive-demo; what to do, which to pick, or whether it is ready is option-cards. Two kinds of ask always put two questions: a review of a change or a draft shows its notes (sitrep) and ends in the verdict (option-cards); a failure or an incident shows what happened (sitrep) before why (zoom-diagram).
- **Order**: sitrep, zoom-diagram, interactive-demo, option-cards, as the reader goes from the situation to the mechanism, to trying, to the choice.
- **drill-it first**: before building, run the `drill-it` skill once, with the settled ask, the placed playbooks' names in order (`sitrep`, `option-cards`, …) as its purposes, and each one's Parts or, for a zoom diagram, its plan; build only from what it hands back.
- **Assembled**: each page playbook writes its part as a fragment; `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/assemble-page.py" <plan.json> <out.html>` builds the page, its usage giving the plan's fields. A zoom diagram's part comes from its playbook's `make-diagram.py part`.

## Delivery

**Delivery follows the ask**: an Artifact when the ask names one or one is in progress, published with the `Artifact` tool; a page embedded in an existing html page when the ask names that page, written into it in its own style; with neither, a temporary HTML file in the scratchpad, sent with `SendUserFile`. Never open a local file in the user's browser.

## Constraints

- **Page parts**: a page playbook's part is a fragment of the Parts its playbook names, with the playbook's CSS and script added by `assemble-page.py`; every table sits in a `.scroll` box. The page opens with the one-sentence answer and closes with the reader's next action; a `.reply` box, which a button's `data-reply` may fill, holds what the reader copies back to you.
- **Only what it needs**: no section, widget or control the answer does not use; a fact that does not change the reader's view is cut, and so is a part that repeats another.
- **Counted as shown**: a count the page states is the count of what it shows.
- **One language**: the page is in the language the user's instructions name, else the ask's; a zoom diagram keeps its terms in English as its `view-writing.md` says.
- **Asking**: the zoom diagram's Interview and drill-it's Undecided go as rounds of `${CLAUDE_PLUGIN_ROOT}/skills/grill-me/SKILL.md` (Asking a round, Settling); recommended options Settling takes stay off the page.

## Done when

1. `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/check-page.py" <page> --shots <dir>` prints `ok` last, and you looked at both captures: the first screen answers the ask, every part reads at 1200 px, and the text agrees with it. A zoom part also passes its playbook's Verification.
2. The page went out as Delivery says, and the chat message gives the one-sentence answer and the next action, nothing more.
