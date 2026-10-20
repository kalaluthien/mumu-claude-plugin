#!/usr/bin/env python3
"""Recount nodes, edges, rules, operations and repeated labels of a toy model; prints one line per file."""
import json, sys, collections
for p in sys.argv[1:]:
    m = json.load(open(p))
    labels = collections.Counter(n["label"] for n in m["nodes"])
    dup = sum(c - 1 for c in labels.values() if c > 1)
    n, e, r, o = len(m["nodes"]), len(m["edges"]), len(m["rules"]), len(m["operations"])
    print(p, f"nodes={n} edges={e} rules={r} operations={o} sum={n+e+r+o} scenarios={len(m['scenarios'])} repeated_labels={dup} per_level={[len(l['nodes']) for l in m['levels']]}")
