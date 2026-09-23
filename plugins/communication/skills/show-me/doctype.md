# Doctypes and media

The doctype is how a document explains; the medium is where it is read. The
question picks the doctype, never the subject.

## Doctypes

| doctype | explains | for | its parts, in order |
| --- | --- | --- | --- |
| `diagram` | in one picture | what it is made of, how its parts connect | the title; the one thing to read off it; the figure; its key; the source |
| `narrative` | in the order understanding builds | how it works, why it is so | a one-line thesis; a map of the whole; chapters, each headed by its answer to one question, with its evidence, never in file or commit order; a reason the source omits, called absent; the source at a sha |
| `comparison` | under one yardstick | which one, or what differs | the question; the verdict and what would change it; the yardstick, fixed before any option; each option against it, bold only on the cells the verdict turns on |

- A repository's structure is a diagram, what a PR changed a comparison, why
  a design is so a narrative.
- Two questions: a narrative, the diagram its map, the comparison a chapter.
- In markdown the parts are headings.

## Media

- **markdown**: GitHub, chat, and always for an agent. Mermaid only in a
  GitHub body.
- **page**: one HTML file for a person, when a layout, a wide table or a
  dense map outgrows markdown. It starts from `page.html` and keeps its
  skin block verbatim.

## Page

- One file: its CSS, SVG, JS and images inline, nothing fetched; opens from
  `file://`.
- Light and dark both, through the skin's tokens.
- Phone width: no sideways page scroll at 320 px, a 16 px gutter; only a
  table, a figure or code scrolls, in its own box with `tabindex="0"` and a
  label.
- No text under 11 px, no Hangul or Han under 12 px.
- `main`, `section`, `figure`, headings in order; native elements before
  ARIA; contrast 4.5:1; visible focus; every control usable by keyboard.
- Reading order is priority order; secondary work in `details`, two levels
  at most.
- No motion of its own; a transition only answers a reader's action.
- Every control is clicked once before delivery, never judged from a
  screenshot.

## Visual encoding

- **Controls**: a control rides on the heading or the element it acts on,
  never a row of its own; a refresh is an icon on the heading with its own
  loading state, and replaces the old reading only when the new one arrives.
- **State**: a state change moves nothing. The verdict travels in colour, an
  icon or a word; what exactly failed is one tap away; one fact takes one
  form everywhere.
- **Content**: labels, values, empty states and errors; no prose about how
  the page behaves. A glyph earns its place only when nothing beside it says
  the same; a short message takes no box.
- **Identity**: plumbing hidden, the work shown: no orchestration status on
  a page for a person.
- **Ordering**: fold a missing signal into the one rank, never a second
  order or a sort the reader picks.

## Figures

- Drawn only where it teaches more than a paragraph; cut it if removing it
  loses nothing.
- At most 9 boxes and 12 arrows, emphasis on 2; over that, an overview and a
  detail.
- Boxes grouped as the reader thinks of the system, never by folder.
- Coordinates divisible by 4; arrows orthogonal with r=8 elbows; a label
  8 px off its line on a background mask.
- One arrow carries a real example value; a changed flow shows before and
  after.
- Every line one-way and labelled; dashed where inferred, not read.
- A key names what was merged, collapsed or dropped; a unit on every scale.
- A compared quantity by position or length on one shared scale, never
  stacked or a pie; a bar axis starts at zero.
- Six colours at most, ground included; hue for kind, lightness for amount;
  the accent only for links and focus.
- SVG ids prefixed per figure: inline SVGs share one id space.

## Prose

- Name things instead of counting them: a count goes stale, a name can be
  grepped.
- A heading on a change says what is true after it, not the subject.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells.

## Check

Run on every page before delivery; `P` is its absolute path. It loads the page
in a true 320 px frame and prints `<scroll>/<client> <smallest text>px` and a
verdict; `pass` needs the two widths equal and no text under 11 px.

```sh
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
F="${TMPDIR:-/tmp}/show-me-frame.html"
cat > "$F" <<'EOF'
<iframe id=f style="width:320px;height:800px;border:0"></iframe>
<script>f.onload=function(){var d=f.contentDocument,e=d.documentElement,w=f.contentWindow,t=d.createTreeWalker(d.body,4),n,s=1/0;while(n=t.nextNode())if(n.data.trim()&&!/^(script|style|title)$/i.test(n.parentElement.tagName))s=Math.min(s,parseFloat(w.getComputedStyle(n.parentElement).fontSize));document.body.dataset.r=e.scrollWidth+'/'+e.clientWidth+' '+s+'px'+(e.scrollWidth==e.clientWidth&&s>=11?' pass':' FAIL')};f.src=location.hash.slice(1)</script>
EOF
"$CHROME" --headless --disable-gpu --allow-file-access-from-files --dump-dom \
  --virtual-time-budget=3000 "file://$F#file://$P" 2>/dev/null |
  sed -n 's/.*data-r="\([^"]*\)".*/\1/p'
```

No output means the frame could not read the page: a wrong path.

## Delivery

- Unless the ask says, ask once with `AskUserQuestion`: chat, a GitHub issue,
  a page, or a page kept in a repository. Do not ask when it is obvious.
- **Chat**: markdown, in the chat forms of `SKILL.md`.
- **GitHub issue**: the body or a comment, by the repository's own procedure,
  else `gh issue create`.
- **Page**: written to `show-me-<slug>.html` in the session's scratch
  directory, checked, then published with the `Artifact` tool when the
  session has it, else opened with `open`.
- **Repository page**: written where the repository keeps pages, checked
  there, linked from its README, landed by its own procedure.
- Whatever the ending, give the one-sentence version in chat.
