# Show

Show a plan to the owner as a page, then read their Answer back into the next plan.

## Domain

### Operations

- The page is a visual tree, one page per Decision and then the Whole plan, after the owner's reference (https://github.com/kalaluthien/mumu-claude-plugin/issues/1009). A reader must judge from the page alone the plan, each choice's consequences, the decision points, the rationale and the expected outcome (https://github.com/kalaluthien/mumu-claude-plugin/issues/1009#issuecomment-6397228825), so nothing needed to judge waits for a hover.
- Its views follow the research of https://github.com/kalaluthien/mumu-claude-plugin/issues/1013#issuecomment-6397221163, and its palette and type follow the html-plan pages (https://github.com/kalaluthien/mumu-claude-plugin/issues/1015#issuecomment-6397317090).
- The owner picks an Option by its number; the other branches fold into one stub, "+ N other options", and a click on it or `Esc` brings them back. The owner strikes a Part with a reason, comments on it or edits its text from the tools on its card; Undo takes back each step before copying.
- On the Whole plan, the Parts after the first Decision not yet answered are faded, never hidden; hover or focus brings one back, and they stay answerable. The fade moves on as each Decision is answered or struck. This is the page's only gate, a view choice; the grammar has none.
- The Whole plan opens with Your choices, one row per Decision with its pick as it stands and what that pick sets off; a click opens the Decision. A click on a card focuses it: its parent, its children and every Part with its `source` stay, the rest fade, and `Esc` or a second click shows all. A card with children folds them to a count.
- One Decision is marked Matters most: the one with the most `risk` Parts under it, then the most Parts under its Options, then the first. The mark names that reason.
- Copy answer, in the bottom bar, writes the Markdown form of [grammar.md](grammar.md) to the clipboard; no box shows it.

### Vocabulary

| plan element | on the page |
| --- | --- |
| Decision text, `source`, child Parts | question card on the left: the source as its author, `risk` children as badges above, the rest as context; Matters most above the one that does |
| Decision `pick`, `else` | numbered cards joined to the question by tree lines, "Agent's pick" on 1, Other as the last number; the unchosen ones faded, the chosen one ringed |
| Option `parts` | facts branching right of the Option: an outcome after an olive dot, a `risk` after a Risk pill, a `note` in full under the fact before it, a `mockup` as a framed screen |
| Option `then` | follow-up question branching right, its options numbered once the Option is picked |
| Part text, `kind`, `source` | a card on the Whole plan with its id and kind, children branching right; `source` a chip, a link when it is a url |
| decision queue | pages: `1 of N` in the header, `←` and `→` between them; the bottom bar names the keys of the step shown |
| every Decision | a row of Your choices at the top of the Whole plan |
| tool icon | dropped: the plan carries no icon |

## Steps

**Show**

1. Run `make-page.py <plan> <out>.html`. The page is one file with no network.
2. Publish the page as an Artifact, or open the file. Tell the owner to press Copy answer and paste the text back.

**Read the Answer back**

1. Save the pasted text as `<name>.answer.md`, unchanged.
2. Run `read-answer.py <plan> <name>.answer.md > <next>.json`. The next plan is on stdout; a refusal prints `refused: line N: <why>` and exits 1.
3. A refused line means the Answer was made from another version of the plan. Show the owner the refusal, never repair the Answer by hand.
4. Run `check-plan.py <next>.json`, then continue the work from the next plan. Its `pick` of each Decision is now the owner's choice.

**Check the page**

`uv run --with playwright==1.64.1 python3 ${CLAUDE_PLUGIN_ROOT}/skills/tree/scripts/make-page.py --check ${CLAUDE_PLUGIN_ROOT}/skills/tree/examples` builds each example, checks which Parts are faded before and after the first pick, answers it in headless Chromium, copies, applies the text and prints `ok 13`.

The same call with `--layout` measures each page as a tree at 1200 px and 390 px and prints `layout ok 13`; `--strategies` drives Your choices, the stub, focus, fold, the mockup frames and the Matters most mark and prints `strategies ok 13`. `--capture <page.html> <dir>` writes four PNGs of a built page to look at, and `--capture-all <page.html> <dir>` every page as a reader first meets it, in screens 700 px apart.
