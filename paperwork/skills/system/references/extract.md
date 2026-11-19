# extract

Find, topic by topic, what a reader needs to rebuild the subject, before any of it is written as a contract.

## Domain

- **finding**: one fact about the subject with the source that shows it: a path, a `path:line`, a url, a command's output or a person's answer.
- **topic**: one kind of thing a rebuild needs; the table below names where each lands in the contract.
- **gap**: what the description lacks or gets wrong, by one of six faults: `missing` (the subject does it, nothing says so), `illegal` (the description allows what the subject forbids), `redundant` (one thing said two ways), `overloaded` (one word for two things), `contradictory` (two sources disagree) and `unknown` (no source settles it).

| topic | look for | lands in |
| --- | --- | --- |
| components and their purpose | each part, and the need it serves | nodes, `purpose` |
| relations between components | who calls, reads, writes, starts or rules whom | edges |
| layers and hierarchy | what is inside what, and how deep | levels, `opens` |
| partitioning and boundaries | modules, owners, trust and deployment lines | areas |
| naming and placement conventions | how a name or a place is chosen | `convention` properties |
| coupling and dependency | what breaks when a part changes | `dependsOn` edges, `fact` properties |
| system documents | specifications, rules and decisions already written | sources |
| state | what is kept, where, in what layout; each lifecycle | `dataStore` and `queue` nodes, regions of `state` nodes |
| control | what starts, orders, routes and stops work | `trigger`, `router` and `policy` nodes, transitions |
| observation | what a run prints, logs or exposes | the `signals` item |
| interfaces and payloads | addresses, signatures, wire formats, constants | `endpoint` nodes, items of `call`, `publish` and `access` edges |
| failure and degraded behaviour | each refusal, error, timeout and retry | the `failure` item |
| scenarios and operational principles | the story that shows each purpose met | scenarios |
| invariants and properties | what always holds, and what must | `invariant` and `property` properties |
| assumptions and constraints | what the subject relies on and may not do | `assumption` and `constraint` properties |
| domain terms and coined words | words a reader would not know | terms |
| rationale | why it is so, and what was turned down | the `why` item |
| deployment and environment | where it runs, on what, set by what | `host` nodes, `deployment` areas |
| security and trust | who may do what, with which secret | `credential` and `policy` nodes, `trustZone` areas |
| actors and outside systems | who starts or receives, outside the subject | `actor` nodes |
| gaps and open questions | what the sources do not settle | `gap` properties |

## Steps

1. Write the rebuild questions before reading closely: for each topic the subject has, what a reader must learn to rebuild it, one thing per question. Extraction ends when each has a sourced answer or a gap.
2. List the sources and what each can settle; a run of the subject settles more than a document about it.
3. Walk the topics in order and note each finding with its source. Copy exact values: a constant, a format, a message, an exit code.
4. For each part, ask what it is for and how that shows: one sentence of purpose, and the shortest story in which a person sees it met.
5. For each thing that changes over time, list its states, the events that move it and what each move does.
6. Climb and descend once: for each part ask why it exists, and for each purpose ask what carries it out; a purpose with no means, or a part with no purpose, is a gap.
7. Replay each story step by step: what a step needs must come from the start or from an earlier step; what nothing supplies is a gap.
8. Compare what the documents say exists with what is stored or run, and name each mismatch by its fault.

## Rules

- **Exact over summary**: a reader rebuilds from the value, so record `0.5 s`, never "polls often".
- **One source each**: a finding with no source is a guess; ask a person, or record a gap.
