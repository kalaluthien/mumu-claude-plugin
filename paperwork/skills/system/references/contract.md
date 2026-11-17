# contract

Write the findings as one contract the checker accepts and a blind reader can rebuild the subject from.

## Domain

A contract is one JSON object. Every record has an `id` of lowercase words joined by `-`, used once in the whole file, a source's and a level's included; a record names another only by its id, and a text names one as `{id}`, shown as that record's label.

- **top**: `title`, `purpose`, `sources`, `terms`, `levels`, `scenarios`, `properties`.
- **source**: `id`, `path` (a file under the subject's root, or a url), `says`, `authority` (what it outranks when two sources disagree). An `evidence` entry is a source id, `id:line` or `id:line-line`; nodes, edges, areas and properties take `evidence` and `basis` (`observed`, `documented` or `inferred`).
- **term**: `term`, `meaning`, `coined` when the subject made the word up.
- **level**: `id`, `title`, `about`, `areas`, `nodes`, `edges`. The first level is the whole subject.
- **node**: `id`, `label`, `tag`, `area` (an area of the node's own level, or left out), `opens` (a level's id), `purpose`, `info`. A label is a noun phrase, such as "the checker".
- **edge**: `id`, `from`, `to`, `label`, `tag`, `many`, `info`; both ends sit on the edge's own level. A static edge's label opens with a verb, so that `<from label> <label> <to label>` is a true and grammatical sentence, the label ending where the `to` label follows, such as "writes" or "takes its items from"; the checker refuses only a label of the wrong form (a capital first, a closing mark or article, a lone preposition, an end's label inside it), and the `read` call shows the writer whether the sentence is true, and it holds for one `to` unless `many` is true, which reads aloud as "each of" before the `to` label: set it only where one `from` relates to several of what the `to` node stands for. A `transition` edge joins two states; its label is the event, and `info` holds its `guard` and `action`.
- **area**: `id`, `label`, `tag`, `info`. An area tagged `region` holds the states of one thing, exactly one current, and names the first in `info.initial`; two regions of a level run side by side. A state answers each event of its region: a transition takes it, or its `ignores` item lists it as changing nothing, its `refuses` item as turned down, or its `terminal` item ends the lifecycle, and then no transition leaves it; `ignores` and `refuses` name an event by its transition's label, and an event that changes no state is listed in `ignores`, since an edge joins two different nodes.
- **info**: the items the element's tag fixes, each in its form: text, number, list, table (`{"columns": [...], "rows": [[...]]}`), tree (`[{"name", "note", "children"}]`) or code.
- **scenario**: `id`, `title`, `purpose`, `principle` (true for the story that shows the contract's purpose met), `steps`. A step is `{"at": <node or edge id>, "note": <60 characters at most>}`: the record it names says what happens.
- **property**: `id`, `kind` (`invariant`, `property`, `fact`, `gap`, `assumption`, `constraint` or `convention`), `strength` (`must`, `should` or `may`; `must` when left out), `status` (`holds`, `broken` or `unknown`; `holds` when left out), `statement`, `on` (ids). A `fact` names two `paths` of edge ids with one start and one end, which must agree; a `gap` names its `fault`, and its `status` is `unknown` when the sources do not settle it, `broken` when two of them disagree, and `holds` when the subject does it and no document says so.

`${CLAUDE_PLUGIN_ROOT}/skills/system/examples/self/contract.json` is a whole one, of this skill; `${CLAUDE_PLUGIN_ROOT}/skills/system/examples/page-changes/contract.json` is a larger one, of a folder of code with eight levels.

## Steps

1. Choose the levels: the whole subject first, with about five to twelve nodes, a deeper level as many as its question needs; open a node into a level only where a rebuild question lies inside it.
2. Write each node with its tag, purpose and the items of its tag; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py tags` prints each tag's items and forms.
3. Write each relation as an edge, and each lifecycle as a region of states joined by transitions.
4. Write the scenarios as paths over those records, and the properties, gaps included.
5. Check: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py check <contract> --root <subject root>` prints `ok`, or each break as `where: rule: message`; the `rules` call says what each rule asks.
6. Read aloud: the `read <contract>` call prints every edge as a sentence and every transition as `state -- event [guard] / action --> state`; correct each line that is false of the subject.
7. Ask the gaps: the `gaps <contract>` call prints what each topic holds and each open question; answer each from the sources by [extract.md](extract.md), or record a `gap` property `on` the record it names.
8. Measure: give the contract alone to a fresh subagent and ask it what it would have to guess to rebuild the subject; each guess is a finding to add or a gap to record.

## Rules

- **One place per word**: a shown word sits in one record's `label`; every other record uses the id, so a rename changes one record.
- **No drawing**: the contract holds no position, colour, size or markup; the page's code decides them.
- **Add, never restate**: a new finding goes into the record it is about; a step's note never repeats what its record says.
- **Gaps stay**: an open question is answered or recorded with its fault, never dropped.
- **Narrowest gap**: a gap's `on` names the smallest record the question is about, since `gaps` asks nothing more of a record a gap names.
- **One level each**: a record sits on one level, the one whose question it answers; another level names it in a text as `{id}`.
- **Angle words are safe**: write a placeholder as a word in angle brackets, such as `<plugin>`; a closing tag, a tag with an attribute or a closing slash, and a tag a browser draws or runs by its name alone, such as `<a>`, `<table>` or `<img>`, is refused as markup; `<script>` alone stays a placeholder, and its closing tag is refused, and so is `{word}` that names no record. Quote the subject's own markup or braces between backticks or in an item of the `code` form, which the page draws as written.
