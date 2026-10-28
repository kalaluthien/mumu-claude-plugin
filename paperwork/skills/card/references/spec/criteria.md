# Criteria

How to write one criterion of a spec. The grammar, [assets/rubric-schema.json](assets/rubric-schema.json), holds its fields; `check-spec.py rules` lists what the checker enforces.

## Rules

- **One proposition**: "and" only for conditions that must hold together, "or" only for equal ways to meet it; split independent achievements. Two or more conjunctions draw a warning.
- **Condition, not judgement**: name the entity, the number with its tolerance, the threshold, the version or the forbidden act. A word such as appropriate, complete or clear (적절, 충분, 명확) needs anchors that say what it means here.
- **Observable**: decide it from the answer alone, never from what the writer meant or knew.
- **Polarity**: `-` means the answer commits the error; an answer that names the error to warn against it does not commit it.
- **Program first**: when a regex or a computation can decide it, mark it a program check; it flips least, so it belongs high.
- **Binary**: a verdict is 0 or 1. A three-level question becomes two criteria, meets fully and meets at least partly.
- **Provenance**: cite where it came from, an expert's failure, a near-miss, an exchange test or the rubric it was migrated from, so a later repair finds why it exists.

## Boundary test

Run each judge criterion over its passing variants and its near-misses, grading as the judge would. A variant it fails means it is too narrow, copied from one exemplar; a near-miss it passes means it is too vague.

## Exchange test

For criteria $k$ and $j$, write two answers: one breaks only $k$ and is better on everything else, the other breaks only $j$. Ask which one the domain expert would ship, with two or three variations. Always the one that keeps $k$: $k$ sits in a higher tier. Split: the same tier. Record every decision; the checker refuses a placement a record contradicts, and needs each criterion tested against a tier peer and against the tier below, so moving a criterion needs a new record. Answers that cycle mean a criterion mixes two propositions: rewrite it. Prefer two to four criterion tiers, since each extra tier shrinks the lower weights geometrically.
