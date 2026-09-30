# Layout

| found, in this order | do |
| --- | --- |
| a model in another checked language (TLA+, Quint, Lean) | use it and the checker the repo runs it with |
| no `alloy` on PATH | say so, name where to get it (alloytools.org), and stop before writing anything; never check a model by reading it |
| `*.als` files | keep their layout; read the model covering the change |
| none | initialise `spec/map.als`, and `spec/<module>/model.als` and `check.als` per module the change touches |
