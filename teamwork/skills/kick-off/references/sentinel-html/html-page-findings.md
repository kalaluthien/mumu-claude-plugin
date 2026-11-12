# HTML page findings

What the scenarios and replays of this playbook show about an HTML page answered by a sentinel, each finding with the log that holds it: `run-logs/page-scenarios-first.txt` and `run-logs/page-scenarios-second.txt` from `run-page-scenarios.cjs`, a live sentinel answering; `run-logs/page-events-replay.txt` from `fixtures/replay-page-events.py`, the server alone; `run-logs/drawing-alone-replay.txt` from `run-drawing-alone.cjs`, the page drawing alone.

## What is text and what is code

Whatever must hold when the sentinel errs is code: the token, the origin check, comment ids, history, Undo, which guest comment is delivered, the escaping of the thread block, the refusal of a stale Accept. Whatever needs judgement is text, the contract's Steps and Rules: what to change, when to ask, when to propose, what lies outside the page.

| part | holds |
| --- | --- |
| the contract | the page's marks and thread block, the event line, the sentinel's Steps and Rules, the server's routes |
| the server | the 127.0.0.1 address behind a random token, the threads, every version, proposals, one line per event, the contract check on each version |
| the page drawing | a badge per anchor, the thread panel, its status, the reload on change, anchors derived from ids and headings |
| the fixtures | one page per contract break and pages that follow it, and the server's recorded answers the drawing is replayed against |

## Findings

1. **A sentinel started by the manager's words alone answers on its page**: it renamed a node, added a linked one and replied under the comment, the drawing showing the node's badge and the answer under the comment (`PASS thread` in `run-logs/page-scenarios-first.txt`).
2. **The page's Undo button puts back a change the sentinel made**, every thread kept (`PASS undo` in `run-logs/page-scenarios-first.txt`); Undo steps back through content changes, a reply alone being none, and never undoes the block the server adds (cases `undo-steps` and `added-block` in `run-logs/page-events-replay.txt`).
3. **A request reaching past the page is refused in the thread**: asked to rename a node and to append to a file beside the page and to a file of the checkout, the sentinel renamed the node, named the rest as outside, and left both files unchanged (`PASS outside` in `run-logs/page-scenarios-second.txt`).
4. **The event line carries no comment text**: it names only the context file, which holds the text, the anchor and the whole thread (case `no-text` in `run-logs/page-events-replay.txt`).
5. **A sentinel's timestamps are guesses**, so the server stamps each sentinel entry when it first sees it and the page shows that time (case `stamped` in `run-logs/page-events-replay.txt`; case `recorded-thread` in `run-logs/drawing-alone-replay.txt`; `PASS status` in `run-logs/page-scenarios-first.txt`).
6. **A guest's comment reaches the sentinel only when it names `@sentinel`**, and a guest's request then counts as a request (case `quiet-guest` in `run-logs/page-events-replay.txt`; `PASS guest` in `run-logs/page-scenarios-second.txt`).
7. **The sentinel asks before a change that can mean two things, and proposes only when asked to**: an ask is answered by a button or by the next typed comment, and a proposal stays off the page until Accept (`PASS ask` and `PASS proposal` in `run-logs/page-scenarios-first.txt`; case `typed-answer` in `run-logs/page-events-replay.txt`).
8. **A proposal saved under another name could not be accepted**, so the server reports an undecided proposal with no file as a contract break, which the sentinel repairs (case `proposal-file` in `run-logs/page-events-replay.txt`).
9. **An Accept of a proposal older than the page's last content change would drop that change**: the server refuses it with its reason and the page shows that reason (case `stale-accept` in `run-logs/page-events-replay.txt`; case `recorded-thread` in `run-logs/drawing-alone-replay.txt`).
10. **A preview is the proposal at the page's own url under a banner in the flow, without the thread panel**, so its links and files load and no comment is sent from it, and it still opens after the decision (cases `plain-preview`, `preview-files` and `decided-preview` in `run-logs/page-events-replay.txt`).
11. **The page reports its own broken block and the sentinel repairs it**, every entry kept; one version of the page file is reported once, however many tabs see it (`PASS repair` in `run-logs/page-scenarios-second.txt`; cases `contract-break` and `error-once` in `run-logs/page-events-replay.txt`).
12. **A sentinel that read the contract once went on by its old text**, so the server says when the contract changes (case `contract-change` in `run-logs/page-events-replay.txt`).
13. **Markup in a comment stays text**: a `</script>` and an `onerror` in a comment ran nothing and the block still parsed (`PASS markup` in `run-logs/page-scenarios-second.txt`).
14. **Only the page's own origin and token may send, and only on 127.0.0.1**: a foreign origin gets 403, a path without the token 404, and the server answers on no other address (`PASS origin` in `run-logs/page-scenarios-second.txt`; cases `token-everywhere` and `local-only` in `run-logs/page-events-replay.txt`).
15. **A page's own files load and the server's records do not**, under any spelling the file system matches (case `sibling-file` in `run-logs/page-events-replay.txt`).
16. **Server edges a page written elsewhere meets**: a `</body>` inside a script string, a thread block with its attributes in another order, and one id counter for comments and errors (cases `body-in-script`, `attribute-order` and `one-counter` in `run-logs/page-events-replay.txt`).
17. **Headings in any script get anchors**, a second same-named one taking `-2`, beside any the page marks (cases `korean-headings` and `marked-and-derived` in `run-logs/drawing-alone-replay.txt`; case `korean-anchor` in `run-logs/page-events-replay.txt`).
18. **Status, badges and selection follow the page**: a quiet note between a comment and its answer leaves the thread waiting, then answered; badges are placed again when the url's hash shows another view or the page rebuilds a part, and left off a part hidden or off the page; a selection goes with one comment and is dropped when the reader clicks it away (cases `status-order`, `hash-views`, `rebuilt-part`, `hidden-parts`, `selection-once` and `selection-dropped` in `run-logs/drawing-alone-replay.txt`; `PASS selection` in `run-logs/page-scenarios-second.txt`).
19. **A thread outlives its part**: a thread whose heading was renamed or whose part was removed is listed apart, still opens and still takes a comment, and the name of a removed part goes to no later part (cases `lost-thread` and `removed-part` in `run-logs/drawing-alone-replay.txt`; fixtures `fixtures/follows-removed-part.html` and `fixtures/follows-diagram-removed-part.html`).
20. **A draft, the open thread and the scroll survive a reload**, and two comments sent at once each get their own answer (`PASS draft` in `run-logs/page-scenarios-first.txt`; `PASS order` in `run-logs/page-scenarios-second.txt`).
21. **One comment changes several parts at once with one reply** (`PASS parts` in `run-logs/page-scenarios-first.txt`).
22. **The contract check reads marks and blocks from the page's elements, not its text**: a mark in a `<code>` or a comment's text is none, a mark on a void element such as `<img>` is one, a mark with no value and `NaN` in the block are breaks (fixtures `fixtures/follows-marks-in-text.html`, `fixtures/follows-void-mark.html`, `fixtures/break-anchors-valueless.html` and `fixtures/break-block-nan.html`; case `contract-fixtures` in `run-logs/page-events-replay.txt`).
23. **The connection works with the page drawing gone, and the drawing with the connection gone**: the server serves the page as written when the drawing folder is deleted, and the drawing draws from the server's recorded answers alone (case `served-as-written` in `run-logs/page-events-replay.txt`; every case of `run-logs/drawing-alone-replay.txt`).

## Limits

- One model at one effort, the light tier at low, answered each scenario once.
- Two writers share one file; the Edit tool's refusal of a file changed since its read is the only lock.
- The contract check reads the file's shape: the form of a sentinel's `id`, the optional fields `working`, `ask` and `proposal`, a thread key written twice and an anchor a page's own script makes are not read.
