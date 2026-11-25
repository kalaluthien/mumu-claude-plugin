# page

Show a checked flow contract as one HTML page a person reads and searches without leaving its diagram.

## Domain

- **page**: one `.html` file made by `make-page.py` from a contract whose levels are all interactions; it refuses a contract with a plan level. The contract is its page data, and each node, edge, task, fragment and milestone is an anchor, so it follows the page rules of [relay.md](../../system/references/relay.md).
- **interaction diagram**: each node a round rectangle across the top, its group's label above its own, filled with its group's light tint and bordered 2 px in its group's colour, one of eight KRDS scales taken in turn; a dashed line runs down from each node, and time flows down. Each edge is one arrow at its own height, its step number in a disc on its sender's line, its name above it as written, its tag's chip and its badges below it, then its `code` items, such as a protocol or a status; an edge from a node to itself is a loop on that node's line; a `reply` is dashed, and an edge that opens a level is bold with a `ref` mark. A fragment is a frame round its edges, the names of its self-calls and the frames inside it with its kind in its top left corner and each operand's guard in brackets, dashed between operands. A milestone is a dotted line across every node's line, its name on it, after the last edge it waits on and below each milestone it waits on.
- **card**: the pointer on a node's line, an edge's arrow or name, a fragment's kind or a milestone's name raises the record's card beside it; a click keeps it, Escape closes it. Its rows, badges and chips are the shared card's; an edge's card gives its step.
- **view**: one level, and the record kept open on it; the address holds it as `#level=…&at=…`. A click on an edge's `ref` mark, or a double-click on the edge, draws the level it opens; the crumbs lead back.
- **search**: `/` opens the shared search over nodes, edges, tasks, fragments, milestones, levels, properties and questions; Enter draws the hit's level and keeps its card.

## Steps

1. Build: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/make-page.py <contract> [<page>]`; a contract the checker refuses builds no page, and its breaks are printed.
2. Hand the page's path to the person, who opens it in a desktop browser.
3. Only when the owner asks to take comments on it, connect and serve the page as [relay.md](../../system/references/relay.md) says; apply a comment to the contract, and build again.

## Rules

- **Code draws**: a change of look or layout goes into [../assets/page.css](../assets/page.css) or [../assets/page.js](../assets/page.js), or, for the card and the search, into the plugin's shared parts [record-card.js](../../../lib/record-card.js), [record-card.css](../../../lib/record-card.css), [record-search.js](../../../lib/record-search.js) and [record-search.css](../../../lib/record-search.css); a change of content goes into the contract; no page is edited by hand.
- **After a change to the page's code**: run `node ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/run-page.cjs`, which must print `PASS`.
