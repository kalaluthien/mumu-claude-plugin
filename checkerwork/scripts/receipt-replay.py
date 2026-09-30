#!/usr/bin/env python3
"""Replay a repository's last commits against the receipt store (task #400).

Usage: receipt-replay.py <checkout> <commits>   (the last <commits> of origin/main, oldest first, empty store to start)

Per commit, each model under spec/ is a run on main; with the change it is a run only when its key, as verify.sh keys,
has no receipt from an earlier commit. Prints the model runs without and with the change, and the commits running none.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import receipt  # noqa: E402


def git(checkout, *args):
    return subprocess.run(["git", "-C", checkout, *args], capture_output=True, text=True, errors="ignore").stdout


def main():
    checkout, commits = sys.argv[1], int(sys.argv[2])
    shas = git(checkout, "rev-list", f"--max-count={commits}", "origin/main").split()[::-1]
    stored, without, with_change, none = set(), 0, 0, 0
    for sha in shas:
        files = [f for f in git(checkout, "ls-tree", "-r", "--name-only", sha, "--", "spec").split() if f.endswith(".als")]
        text = {f: git(checkout, "show", f"{sha}:{f}") for f in files}
        models = [f for f in files if receipt.is_model(text[f])]
        keys = {receipt.model_key(m, text.get) for m in models}
        runs = len(keys - stored)
        stored |= keys
        without += len(models)
        with_change += runs
        none += runs == 0
    pct = round(100 * with_change / without) if without else 0
    print(f"model runs on main {without}, with changed-only {with_change} ({pct}%), commits running none {none}")


if __name__ == "__main__":
    main()
