# Show

Show a plan to the owner as a page, then read their Answer back into the next plan.

## Domain

### Operations

- The first Decision is selected on load, so a number works at once. Press a number to pick an Option; when it has a follow-up, a hint `Then 1 – K` shows and the next number picks there. The last number opens Other.
- Press `j` or `k` to move between Decisions, `Esc` to close Other or a note.
- Strike a Part with a reason, comment on it, or edit its text; each can be undone before copying.
- The Parts after the first Decision not yet answered are faded, never hidden; hover or focus brings one back, and they stay answerable. The fade moves on as each Decision is answered or struck. This is the page's only gate, a view choice; the grammar has none.
- Copy Answer writes the Markdown form of [grammar.md](grammar.md) to the clipboard.

### Vocabulary

| plan element | on the page |
| --- | --- |
| Part text, `kind` | tree line with its id and a small kind label |
| `kind: risk` | amber label and text |
| `source` | small chip; a link when it is a url |
| Decision `pick`, `else` | numbered card, "Agent's pick" on 1, Other as the last number |
| Option `parts` | consequences and notes under the Option, before the choice |
| Option `then` | follow-up shown under its Option, awake after the Option is picked |
| decision queue | one card per Decision, `j` and `k` between them, not a pager |
| tool icon, hover fade | dropped: the view only; the plan carries no icon |

## Steps

**Show**

1. Run `check-plan.py <plan>`; stop unless it prints `ok 1`.
2. Run `make-page.py <plan> <out>.html`. The page is one file with no network.
3. Publish the page as an Artifact, or open the file. Tell the owner to press Copy Answer and paste the text back.

**Read the Answer back**

1. Save the pasted text as `<name>.answer.md`, unchanged.
2. Run `read-answer.py <plan> <name>.answer.md > <next>.json`. The next plan is on stdout; a refusal prints `refused: line N: <why>` and exits 1.
3. A refused line means the Answer was made from another version of the plan. Show the owner the refusal, never repair the Answer by hand.
4. Run `check-plan.py <next>.json`, then continue the work from the next plan. Its `pick` of each Decision is now the owner's choice.

**Check the page**

`uv run --with playwright==1.64.1 python3 ${CLAUDE_PLUGIN_ROOT}/skills/tree/scripts/make-page.py --check ${CLAUDE_PLUGIN_ROOT}/skills/tree/examples` builds each example, checks which Parts are faded before and after the first pick, answers it in headless Chromium, copies, applies the text and prints `ok 12`.
