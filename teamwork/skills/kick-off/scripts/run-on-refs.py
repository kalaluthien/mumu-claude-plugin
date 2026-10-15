#!/usr/bin/env python3
"""usage: run-on-refs.py <command> <base ref> <ref>...

Run one shell command in an exported copy (`git archive`) of each ref, so a test kept in the scratchpad runs on the
default branch and on the head without entering either checkout. Prints the command's output and its exit code per
ref, then whether it fails on the base ref and passes on every other ref, which is what a throwaway test must show."""
import shutil
import subprocess
import sys
import tempfile

command, *refs = sys.argv[1:]
if len(refs) < 2:
    sys.exit(__doc__)
codes = {}
for ref in refs:
    sha = subprocess.run(["git", "rev-parse", "--short", ref], capture_output=True, text=True, check=True).stdout.strip()
    copy = tempfile.mkdtemp(prefix="run-on-refs-")
    try:
        archive = subprocess.Popen(["git", "archive", ref], stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", copy], stdin=archive.stdout, check=True)
        archive.wait()
        codes[ref] = subprocess.run(["sh", "-c", command], cwd=copy).returncode
    finally:
        shutil.rmtree(copy)
    print(f"{ref} {sha}: exit {codes[ref]}", flush=True)
base, *heads = refs
if codes[base] and not any(codes[h] for h in heads):
    print(f"fails on {base}, passes on {', '.join(heads)}")
else:
    print(f"does not fail on {base} and pass on {', '.join(heads)}: the command does not show the change")
