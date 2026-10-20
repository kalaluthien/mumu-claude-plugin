# Mermaid

The default renderer: a Schema document shown in chat as Markdown, with no page to open.

Run `scripts/emit-mermaid.py doc.json`, the path relative to this file. Print its output into the reply unchanged; it is deterministic, so the same document always reads the same. The output is:

1. a file tree of the levels, each named `<id>: <title> (<kind>[, view|nest])`, where the root's id is `root` and every other level takes the id of the node that opens it;
2. one Mermaid block per level, in tree order, top level first;
3. under each block, the level's syncs as a list and its metadata as a table, shown as [formats.md](formats.md) says.

Run `emit-mermaid.py --check doc.json` when a block looks short: it names each level, node or edge the output lacks.

## Drawing by kind

Each kind is drawn as its reading in [semantics.md](../schema/semantics.md) says:

- [Topology](../schema/semantics.md#topology): a top-down `flowchart`. A component is a box, an abstract type a parallelogram, a singleton a double box, and a relation an arrow labelled with its field.
- [Workflow](../schema/semantics.md#workflow): a left-to-right `flowchart`. An activity is a rounded box, a fork or join a hexagon labelled `(fork)` or `(join)`, and a partition a subgraph. A trigger is a circle and a port a flag, each with an arrow into or out of the flow.
- [State](../schema/semantics.md#state): a `stateDiagram-v2` titled by its subject. The initial state takes `[*] -->`, and a trigger takes `[*] -->` with its label. Orthogonal regions are compartments split by `--`, each named after its region. A sync is listed under the block, since Mermaid draws no arrow between regions' events.

On every kind:

- A node that opens a level ends with `▸`.
- A `qty` follows the label as `<value> <unit> (<kind>)`.
- On an arrow, `happy` is thick, `failure` dotted red with `✗`, `optional` dotted, and `unsure` dotted with `?`.
- On a node, a mark is a coloured or dashed outline, and a `diff` tints the node.

## Losses

What survives the projection into Mermaid. A construct is `kept` when changing it changes the output, and `emit-mermaid.py losses` checks every row of this table that way. A lost construct is still in the document, for the HTML renderer or a reader of the JSON.

| construct | survives | how |
| --- | --- | --- |
| `document.title` | kept | the heading |
| `document.plan` | lost | the author's intent, not a drawing |
| `document.types` | lost | Alloy types |
| `document.scenarios` | lost | animated on the HTML page instead |
| `document.operations` | lost | Alloy operations |
| `document.rules` | lost | Alloy rules |
| `document.level` | kept | the tree and every block |
| `document.version` | lost | the grammar version |
| `document.meta` | kept | a line under the heading |
| `level.kind` | kept | the diagram type and the heading |
| `level.title` | kept | the tree and the heading |
| `level.why` | kept | an italic line under the heading |
| `level.subject` | kept | the heading of a state level, `(state of <subject>)` |
| `level.initial` | kept | `[*] -->` |
| `level.init` | lost | an Alloy predicate |
| `level.partitions` | kept | subgraphs |
| `level.triggers` | kept | a circle, or `[*] -->`, with its label |
| `level.syncs` | kept | the list under the block |
| `level.in` | kept | a flag into the flow, or `[*] -->` |
| `level.out` | kept | a flag out of the flow, or `--> [*]` |
| `level.media` | lost | too long for a diagram |
| `level.nodes` | kept | nodes and states |
| `level.edges` | kept | arrows |
| `level.regions` | kept | compartments split by `--` |
| `level.refs` | lost | sources, not a drawing |
| `level.meta` | kept | the `this level` row of the table |
| `node.id` | kept | the Mermaid id `n_<id>` and the table |
| `node.label` | kept | the node's text |
| `node.what` | lost | too long for a node |
| `node.partition` | kept | the subgraph that holds it |
| `node.abstract` | kept | a parallelogram |
| `node.singleton` | kept | a double box |
| `node.attrs` | lost | type detail |
| `node.ops` | lost | Alloy operations |
| `node.rules` | lost | Alloy rules |
| `node.mark` | kept | an outline style |
| `node.refs` | lost | sources, not a drawing |
| `node.media` | lost | too long for a diagram |
| `node.opens` | kept | `▸` and the child level |
| `node.region` | kept | the compartment that holds it |
| `node.qty` | kept | a line under the label |
| `node.meta` | kept | a row of the table |
| `node.link` | kept | `view` or `nest` in the tree |
| `node.gate` | kept | a hexagon labelled `(fork)` or `(join)` |
| `edge.from` | kept | the arrow's tail |
| `edge.to` | kept | the arrow's head |
| `edge.label` | kept | the arrow's text |
| `edge.what` | lost | too long for an arrow |
| `edge.ops` | lost | Alloy operations |
| `edge.rules` | lost | Alloy rules |
| `edge.is` | lost | type detail |
| `edge.attr` | lost | type detail |
| `edge.mark` | kept | the arrow's style and sign |
| `edge.refs` | lost | sources, not a drawing |
| `edge.media` | lost | too long for a diagram |
| `edge.qty` | kept | after the arrow's text |
| `edge.meta` | kept | a row of the table |
| `meta.note` | kept | per formats.md |
| `meta.diff` | kept | per formats.md |
| `meta.evidence` | kept | per formats.md |
| `meta.constraint` | kept | per formats.md |
| `meta.<name>-text` | kept | per formats.md |
| `meta.<name>-number` | kept | per formats.md |
| `meta.<name>-url` | kept | per formats.md |
| `meta.<name>-ms` | kept | per formats.md |
| `meta.<name>-percent` | kept | per formats.md |
| `meta.<name>-date` | kept | per formats.md |
| `meta.<name>-bool` | kept | per formats.md |
| `level.kind=topology` | kept | a top-down flowchart |
| `level.kind=workflow` | kept | a left-to-right flowchart |
| `level.kind=state` | kept | a state diagram |
| `node.mark=happy` | kept | a thick green outline |
| `node.mark=failure` | kept | a red outline |
| `node.mark=optional` | kept | a dashed outline |
| `node.mark=unsure` | kept | a grey dotted outline |
| `edge.mark=happy` | kept | a thick arrow |
| `edge.mark=failure` | kept | a dotted red arrow with `✗` |
| `edge.mark=optional` | kept | a dotted arrow |
| `edge.mark=unsure` | kept | a dotted arrow with `?` |
| `node.link=view` | kept | `view` in the tree |
| `node.link=nest` | kept | `nest` in the tree |
| `node.gate=fork` | kept | `(fork)` |
| `node.gate=join` | kept | `(join)` |
