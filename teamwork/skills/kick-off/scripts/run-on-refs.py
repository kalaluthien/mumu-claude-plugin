#!/usr/bin/env python3
"""Run one shell command in an exported copy (`git archive`) of each ref, so a test kept in the scratchpad runs on the
base and on the head without entering either checkout. Prints the command's output and its exit code per
ref, then whether it fails on the base ref and passes on every other ref, which is what a throwaway test must show.

usage: run-on-refs.py <command> <base ref> <ref>..."""
import shutil
import subprocess
import sys
import tempfile


def main(args):
    if len(args) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    command, *refs = args
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
    if codes[base] and not any(codes[head] for head in heads):
        print(f"fails on {base}, passes on {', '.join(heads)}")
    else:
        print(f"does not fail on {base} and pass on {', '.join(heads)}: the command does not show the change")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
