# page

Show a checked contract as one HTML page a person reads, searches and plays without leaving its diagram.

## Domain

- **page**: one `.html` file made by `make-page.py` from a contract, with its style, code and data inline; it asks the network for nothing and opens from disk. The contract is its page data, and each node, edge and area is an anchor, so it follows the page rules of the `relay` skill.
- **diagram**: one level drawn to fill the window: each node a rectangle with its label and its tag's name, each area a frame, each edge a curve with its label; a label that would cover another thing shows only while its edge is under the pointer or picked.
- **overlay**: the card beside the node, edge or area under the pointer, one row per item in the item's form; a click keeps it open and Escape closes it.
- **view**: a level, the record picked on it, and a scenario with its step; every move makes one, the address holds it as `#level=…&at=…&scenario=…&step=…`, and the browser's back and forward, or `[` and `]`, walk the views in order.
- **search**: `/` opens it. A query matches a record's name first, then its id, tag, sentence and other texts: the whole name, a word, the start of a word, the first letters of its words, then a word one or two slips away; a query typed with the Korean two-set layout left on is read as the keys pressed. Opened empty it lists the rebuild questions first; a question, listed or found by its words, leads to the first record that answers it, or to the gap it is left to.

`${CLAUDE_PLUGIN_ROOT}/skills/system/examples/self/page.html` and `${CLAUDE_PLUGIN_ROOT}/skills/system/examples/page-changes/page.html` are the pages of the two example contracts.

## Steps

1. Build: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/make-page.py <contract> [<page>]` checks the contract, then writes the page beside it as `page.html`, or at `<page>`; a contract the checker refuses builds no page and its breaks are printed.
2. Hand the page's path to the person, who opens it in a desktop browser.
3. To take the person's comments on it, connect and serve the page as the `relay` skill says; apply a comment to the contract, build again, and never edit the page.

## Rules

- **Code draws**: a change of look, layout or motion goes into [../assets/page.css](../assets/page.css) or [../assets/page.js](../assets/page.js), and a change of content into the contract; no page is edited by hand.
- **After a change to the page's code**: build each example's page again, then run `node ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/run-page.cjs`, which opens the pages in a headless browser at three desktop sizes and must print `PASS`.
