# contract

The records every paperwork contract holds, whatever its skill; each skill's `contract.md` adds its own records and rules.

## Domain

- **contract**: one JSON object, or a folder of its parts. A record names another only by its id, lowercase words and digits joined by `-`, used once in the whole contract; a text names a record as `{id}`, shown as that record's label.
- **source**: `id`, `path` (a file under the subject's root, or a url), `says`, `authority` (what it outranks when two sources disagree). A record that cites one takes `evidence`, each entry a source id, `id:line` or `id:line-line`, and `basis` (`observed`, `documented` or `inferred`).
- **term**: `term`, `meaning`, `coined` when the subject made the word up, `avoid`, `aliases`.
- **level**: `id`, `title` (a slug, the name the page lists it by), `about`: one view of the subject. The first level is the whole subject, which nothing opens; every other is opened by the record whose inside it shows, which names it in `opens`, and no chain of `opens` leads back to a level it starts from.
- **tag**: what kind a record is, which fixes the items of its `info`, each with a `name` (its key in `info`), a `label` (its shown name) and a `form`: text, number, list, table (`{"columns": [...], "rows": [[...]]}`), tree (`[{"name", "note", "children"}]`) or code. `tags.json` here holds the forms and every tag and common item both skills use; a skill's `assets/tags.json` holds only its own, and every reader merges it over this one.
- **area**: `id`, `label`, `purpose`, `aliases`, `evidence`, `basis`: a named set of nodes drawn as one box, such as a team, a module or a data centre. A node names its area in `area`, and an area holds one node at least.
- **claim**: `id`, `title` (a slug, the name the page lists it by), `kind`, `strength` (`must`, `should` or `may`; `must` when left out), `status`, `fault`, `source`, `statement`, `on` (the ids of the records it is about), `paths`, `evidence`, `basis`.
  - `kind` is `guarantee`, what the subject keeps true, or `assumption`, what it takes the world outside to be, after Zave and Jackson (https://doi.org/10.1145/237432.237434).
  - `status` is `holds` (when left out), `fails`, `conflicting` (two sources disagree) or `unknown` (no source settles it); `fault`, never blank, says why whenever it is not `holds`, and on a `holds` claim no document states.
  - `source` names the source that set the claim, such as the style guide behind a naming rule.
  - `paths` are two chains of edge ids with one start and one end, which must agree; only a guarantee holds them, with no `status`, since the checker settles it.
- **question**: `id`, `asks` (one thing a reader must learn), `answers`: the records that answer it, one at least with evidence, or the claim whose `fault` says why no source does.
- **part**: a contract of many levels kept as a folder that the skill's `split` call writes: `top.json`, every record no level holds, and `levels/<id>.json`, one level with the records it holds. Every script takes the folder where it takes the file, and a task's criterion names a part by its file's path.

Both checkers check these records by one definition, `contract_core.py`, and word its rules alike in their `rules` call: `unique-ids`, `area-known`, `level-links`, `claim-form`, `claim-paths`, `evidence-source` and `question-answered`.
