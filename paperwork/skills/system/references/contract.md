# contract

Write the findings as one contract the checker accepts and a blind reader can rebuild the subject from.

## Domain

A contract is one JSON object. A record names another only by its id, and a text names a node, an edge or an area as `{id}`, shown as that record's label.

- **top**: `title`, `purpose`, `sources`, `terms`, `levels`, `areas`, `nodes`, `edges`, `scenarios`, `properties`, `questions`; the nodes, edges and areas are one list each for the whole subject, and a level is a view of them.
- **source**: `id`, `path` (a file under the subject's root, or a url), `says`, `authority` (what it outranks when two sources disagree). Nodes, edges, areas and properties take `evidence` and `basis` (`observed`, `documented` or `inferred`).
- **term**: `term`, `meaning`, `coined` when the subject made the word up, `avoid`, `aliases`.
- **aliases**: a node, an area or a term may list in `aliases` the words a reader searches it by that its name lacks, such as `아마존` for `AWS`; the page's search finds a node or an area by each as by its name, and takes a term's alias for the term itself; [writing.md](writing.md) says which to write.
- **level**: `id`, `title` (a slug, such as `inside-server`), `about`. It shows the nodes and areas whose `level` names it and the edges that leave those nodes, one node at least. The first level is the whole subject.
- **node**: `id`, `label`, `tag`, `level` (the level that shows it), `area` (an area of the node's own level, or left out), `opens` (a level's id), `files` (the ids of the sources that are this node, where it is one or more files), `purpose`, `info`, `aliases`.
- **edge**: `id`, `from`, `to`, `label`, `tag`, `many`, `info`; the id says what the edge does, such as `takes-items`, and holds neither end's id, so moving an end leaves it true. A static edge reads as the sentence `<from label> <label> <to label>`, which holds for one `to` unless `many` is true, read aloud as "each of" before the `to` label: set it only where one `from` relates to several of what the `to` node stands for. A `transition` edge joins two states; its label is the event, and `info` holds its `guard` and `action`.
- **area**: `id`, `label`, `tag`, `level`, `info`, `aliases`. An area tagged `region` holds the states of one thing, exactly one current, and names the first in `info.initial`; two regions of a level run side by side. A state answers each event of its region: a transition takes it, or its `ignores` item lists it as changing nothing, its `refuses` item as turned down, or its `terminal` item ends the lifecycle; `ignores` and `refuses` name an event by its transition's label, and an event that changes no state is listed in `ignores`, since an edge joins two different nodes.
- **info**: the items the element's tag fixes, each in its form: text, number, list, table (`{"columns": [...], "rows": [[...]]}`), tree (`[{"name", "note", "children"}]`) or code.
- **scenario**: `id`, `title` (a slug), `purpose`, `principle` (true for the story that shows the contract's purpose met), `steps`. A step is `{"at": <node or edge id>, "note": <text>}`: the record it names says what happens.
- **property**: `id`, `title` (a slug, the name the page lists it by), `kind` (`invariant`, `property`, `fact`, `gap`, `assumption`, `constraint` or `convention`), `strength` (`must`, `should` or `may`; `must` when left out), `status` (`holds`, `broken` or `unknown`; `holds` when left out), `statement`, `on` (ids). A `fact` names two `paths` of edge ids with one start and one end, which must agree; a `gap` names its `fault`, and its `status` is `unknown` when the sources do not settle it, `broken` when two of them disagree, and `holds` when the subject does it and no document says so.
- **question**: `id`, `asks` (one thing a reader must learn to rebuild the subject), then `answers` or `gap`.

`${CLAUDE_PLUGIN_ROOT}/skills/system/examples/self/contract.json` is a whole one, of this skill; `${CLAUDE_PLUGIN_ROOT}/skills/system/examples/page-changes/contract.json` is a larger one, of a folder of code with eight levels.

## Steps

1. Copy the rebuild questions [extract.md](extract.md) wrote into `questions`, each with no answer yet.
2. Choose the levels: the whole subject first, with about five to twelve nodes, a deeper level as many as its question needs; open a node into a level only where a rebuild question lies inside it.
3. Word every text by [writing.md](writing.md). Write each node with its tag, purpose and the items of its tag; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py tags` prints each tag's items and forms, and [tags.md](tags.md) says where each tag comes from and when a new one is earned. An item holds what the subject says, in its form: `terminal` holds what ends there, such as "the order is archived".
4. Write each relation as an edge, and each lifecycle as a region of states joined by transitions.
5. Write the scenarios as paths over those records, and the properties, gaps included.
6. Check: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py check <contract> --root <subject root>`; the `rules` call says what each rule asks.
7. Read aloud: run the `read <contract>` call and correct each line that is false of the subject.
8. Ask the gaps: run the `gaps <contract>` call and answer each open question from the sources by [extract.md](extract.md), or record a `gap` property `on` the record it names.
9. Score: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/score-contract.py <contract> --root <subject root>` and correct each quoted value it prints, or its evidence.
10. Sort the edges: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/sort-edges.py <contract> --root <subject root>`; for each relation it prints, add the edge, correct it, or record a gap.
11. Measure: give the contract alone to a fresh subagent and ask it what it would have to guess to rebuild the subject; each guess is a finding to add or a gap to record.

## Rules

- **One place per word**: a shown word sits in one record's `label`; every other record uses the id, so a rename changes one record.
- **No drawing field**: no record holds a field for a position, a colour or a size; the page's code decides them.
- **Catalogue apart**: an item's key in `info` is the catalogue's `name`, never shown; its shown name is the catalogue's `label`, so a new shown name changes `assets/tags.json` alone, and an item given another form changes the catalogue and the records that hold it, which `check <contract> --tags <file>` checks against a changed copy first; `statement`, `guard`, `action`, `initial` and `terminal` stay text and `ignores` and `refuses` lists, since the `read` and `gaps` calls read them so, and a catalogue that reforms one, in its tag or among the common items, renames one, or lacks a tag's `meaning` or an item's `label` or `example`, or holds a tag's items as other than a list of records, is refused; the catalogue fixes each item in one record, so a tag never fixes an item every element of its kind holds.
- **Add to its record**: a new finding goes into the record it is about, and a step names that record instead of saying it again.
- **Narrowest gap**: a gap's `on` names the smallest record the question is about, since `gaps` asks nothing more of a record a gap names.
- **One level each**: a node or an area names one level, the one whose question it answers, so moving one that no edge or area holds changes its record alone, and the checker names each edge and area a held one would strand, which move or are cut with it; another level names it in a text as `{id}`.
