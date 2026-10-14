---
name: show-me
description: Use to see something as a page instead of prose - a system, options, a change, where things stand, or a value to tune.
disable-model-invocation: true
---

# show-me

**Seen or not done**: describing a picture in prose, or naming a file path, is not showing it. Show the topic named, else the conversation's.

## Routing

Pick the row by what the reader wants done, never by the topic's look, and read its playbook before building. One page answers one intent; a second intent is a second page or a short part of the first.

| the ask is to … | playbook |
| --- | --- |
| analyse, design or learn a whole system, even one whose parts have choices: software, a process, a protocol, an organization, a body of knowledge | [references/zoom-diagram/zoom-diagram.md](references/zoom-diagram/zoom-diagram.md) |
| choose among named alternatives: approaches, designs, layouts, tools | [references/option-cards.md](references/option-cards.md) |
| review a change or a text: a pull request, a diff, a draft | [references/margin-notes.md](references/margin-notes.md) |
| know where things stand or what happened: status, a trend, an incident | [references/chart-brief.md](references/chart-brief.md) |
| set a value best judged by seeing it: a colour, a timing, a prompt, a config | [references/live-controls.md](references/live-controls.md) |

An answer that fits on one screen as a table or a short fenced tree needs no page: give it in chat.

**drill-it first**: before building, run the `drill-it` skill with the settled ask, the playbook's title as its purpose, and the playbook's Parts or, for a zoom diagram, the plan; build only from what it hands back.

## Delivery

**Delivery follows the ask**: an Artifact when the ask names one or one is in progress, published with the `Artifact` tool; a page embedded in an existing html page when the ask names that page, written into it in its own style; with neither, a temporary HTML file in the scratchpad, sent with `SendUserFile`. Never open a local file in the user's browser.

## Constraints

- **Page parts**: a page playbook fills `${CLAUDE_PLUGIN_ROOT}/skills/show-me/assets/base-page.html`; its Parts says what each body part holds, its CSS goes after the base page's, and every table sits in a `.scroll` box.
- **Only what it needs**: no section, widget or control the answer does not use; a fact that does not change the reader's view is cut, and so is a part that repeats another.
- **Counted as shown**: a count the page states is the count of what it shows.
- **One language**: the page is in the language the user's instructions name, else the ask's; a zoom diagram keeps its terms in English as its `model-writing.md` says.
- **Asking**: the zoom diagram's Interview, and what drill-it puts to the user, go as one round of `${CLAUDE_PLUGIN_ROOT}/skills/grill-me/SKILL.md` (Asking a round), each with a proposed answer; when no one can answer (a non-interactive run), take the proposed answers and state them in the hand-over, never on the page.

## Done when

1. `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/check-page.py" <page> --shots <dir>` prints `ok` last, and you looked at both captures: the first screen answers the ask, the central figure (chart, cards, rows or controls) reads at 1200 px, and the text agrees with it. A zoom diagram is done by its playbook's Procedure and Verification instead.
2. The page went out as Delivery says, and the chat message gives the one-sentence answer and the next action, nothing more.
