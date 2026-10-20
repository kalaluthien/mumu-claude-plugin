# Hand-back
## Facts
Original (models/original.json): nodes 8, edges 6, rules 2, operations 4, sum 20. Repeated labels 1 ("Bill customer"). Level sizes 3 and 5, depth 2.
## Not verified
Runtime behaviour of the shop.
## Undecided
Whether refunds need their own node.
## Findings
Two nodes share the label "Bill customer"; the edge bill-refund joins them.
## Options
### Option A (recommended): merge bill and refund (models/improved.json)
Added: none. Removed: node refund (merged into bill). All Scenarios and rules kept.
| count | original | A | B |
| --- | --- | --- | --- |
| nodes+edges+rules+operations | 20 | 18 (7+5+2+4) | 17 (7+5+1+4) |
| repeated labels | 1 | 0 | 0 |
| level sizes | 3, 5 | 3, 4 | 3, 4 |
| scenarios kept | 2 | 2 | 1 |
| four states | 1 Redundant | none | none |
### Option B: also drop order-returned and no-bill-twice (models/improved-b.json)
Removed, awaiting approval: Scenario order-returned, rule no-bill-twice. Conflict: size (B smaller by 1) against kept behaviour (B loses two items).
