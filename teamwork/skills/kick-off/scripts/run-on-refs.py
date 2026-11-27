#!/usr/bin/env python3
"""Run one shell command in an exported copy (`git archive`) of each ref, so a test kept in the scratchpad runs on the
base and on the head without entering either checkout. Prints the command's output and its exit code per
ref, then whether it fails on the base ref and passes on every other ref, which is what a throwaway test must show.

usage: run-on-refs.py <command> <base ref> <ref>... [--repository <folder>]"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import data_folder  # noqa: E402


def main(args):
    args = data_folder.enter(args, __doc__)
    if len(args) < 3 or any(argument.startswith("--") for argument in args):
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
