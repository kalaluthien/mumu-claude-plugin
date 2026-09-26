# Folder leads

The rules of a lead in a repository with `scope:` labels.

A repository with `scope:<folder>` labels (`gh label list --search scope:`) runs one lead per plugin folder, each at the checkout root, and no `<repo>-lead`.

- Your folder is the `scope:` label of the goal you were started or handed, else the plugin folder its words name: `name` yourself `<folder>-lead`. Label `scope:<folder>` each root goal and root task you hold, a received goal with no `scope:` label included (`gh issue edit <url> --add-label scope:<folder>`), and add `--label scope:<folder>` to every `gh issue list` of them; the Stop hook and `team-watch` still read every one.
- Act only on a worker whose task is, or sits under, a root goal or root task you hold, labelled `scope:<folder>`: `team-watch` lists every worker of the checkout, each lead's alike.
- Agreement: before changing another folder's files, taking a goal across folders, or a shared operation that touches other leads (`clean`'s pull, `tab-sweep.py`, `/reload-plugins`), propose it to every live lead of the folders concerned, found with `ListAgents`, through `SendMessage`, and act after their answers. The talk is not recorded; only what it leads to is, as usual (a label, an `order`, a `DECIDED:`). An objection: revise and ask again; two proposals colliding: the one sent first wins; past two objections, or no answer after one resend at the next `team-watch` line: ask the owner. Work across folders is led by the lead that received it first.
