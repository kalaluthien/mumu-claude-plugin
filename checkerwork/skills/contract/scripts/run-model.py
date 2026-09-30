#!/usr/bin/env python3
"""Put an Alloy model's receipt in <outdir>/receipt.json: the stored one, else from `alloy exec`, which is then stored.

Usage: run-model.py <model> <outdir> <log>   (run from the repo root; a model that did not parse leaves no receipt)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import receipt  # noqa: E402

model, out, log = sys.argv[1:4]
store = receipt.store_dir()
key = receipt.model_key(model, receipt.read_file)
text = receipt.load(store, key) if store else None
if text is not None:
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "receipt.json"), "w") as f:
        f.write(text)
    sys.exit(0)
with open(log, "w") as f:
    subprocess.run(["alloy", "exec", "-f", "-q", "-o", out, model], stdout=f, stderr=subprocess.STDOUT)
text = receipt.read_file(os.path.join(out, "receipt.json"))
if store and receipt.valid(text):
    receipt.save(store, key, text)
