# Changelog

Each version of the grammar, [assets/schema.json](assets/schema.json), newest first. A document names the version it is
written in; a script that reads an older one migrates it.

## 1

- First version, from paperwork's system model: the kind `schema` is now `topology`, and a document names its
  `version`.
- `link` marks how a node opens its level: `view` for another kind, `nest` for the same kind with no interface claim.
- `gate` marks a workflow fork or join.
- `meta` on a document, level, node or edge, its formats in `$defs.format`.
- Ids, slugs, operations and type names have patterns.
