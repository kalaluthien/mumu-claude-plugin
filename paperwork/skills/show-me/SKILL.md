---
name: show-me
description: Use when the user asks to see something rather than read about it - show, draw, map, walk through, explain, teach, compare, report or offer options - or when you are about to describe a system, a layout, a plan, a change or numbers in prose. Not when the answer is still the user's to make (grill-me).
---

# show-me

**Seen or not done**: describing a picture in prose, or naming a file path, is not showing it. Show the topic named, else the conversation's.

## Routing

Pick the row by what the reader wants done, never by the topic's look, and read its playbook before building: one system to design or understand is a zoom diagram, even when its parts have choices; named alternatives to pick from are option cards. One page has one main form; a second intent is a second page or a short part of the first.

| the ask is to … | playbook |
| --- | --- |
| analyse, design or learn a whole system: software, a process, a protocol, an organization, a body of knowledge | [references/zoom-diagram/zoom-diagram.md](references/zoom-diagram/zoom-diagram.md) |
| choose among options: approaches, designs, layouts, tools | [references/option-cards.md](references/option-cards.md) |
| review a change or a text: a pull request, a diff, a draft | [references/margin-notes.md](references/margin-notes.md) |
| know where things stand or what happened: status, a trend, an incident | [references/chart-brief.md](references/chart-brief.md) |
| set a value best judged by seeing it: a colour, a timing, a prompt, a config | [references/live-controls.md](references/live-controls.md) |

An answer that fits on one screen as a table or a short fenced tree needs no page: give it in chat.

## Output

**Output follows the ask**: an Artifact when the ask names one or one is in progress, published with the `Artifact` tool; a page embedded in an existing html page when the ask names that page, written into it in its own style; with neither, a temporary HTML file in the scratchpad, sent with `SendUserFile`. Never open a local file in the user's browser.

## Rules

- **Page parts**: a page playbook fills `${CLAUDE_PLUGIN_ROOT}/skills/show-me/assets/base-page.html`; its Form says what each body part holds, and every table sits in a `.scroll` box.
- **Only what it needs**: no section, widget or control the answer does not use; a fact that does not change the reader's view is cut, and so is a part that repeats another.
- **Checked facts**: every name, number, status and path comes from a file read, a command run or a page opened in this session; one not checked says "not verified"; a count the page states is the count of what it shows.
- **One language**: the page, labels included, is in the language the user's instructions name, else the ask's.
- **No one to ask**: when a playbook says to ask the user and no one can answer (a non-interactive run), take your proposed answers and say so on the page.

## Done when

1. `"${CLAUDE_PLUGIN_ROOT}/skills/show-me/scripts/check-page.py" <page> --shots <dir>` prints `ok` last, and you looked at both captures: the first screen answers the ask, the main form reads at 1200 px, and text and figure agree. A zoom diagram passes its own `make` instead, and you looked at its `render --shots` captures the same way.
2. The page went out as Output says, and the chat reply gives the one-sentence answer and the next action, nothing more.
