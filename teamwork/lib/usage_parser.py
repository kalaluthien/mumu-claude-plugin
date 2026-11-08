"""Makes an argparse parser that answers a call it cannot read as AGENTS.md's Script form says."""
import argparse
import sys


def parser(doc, **options):
    """An ArgumentParser that prints DOC on stderr and exits 2 on a call it cannot read, instead of argparse's own usage line, and reads `--help` as the unknown option it is."""
    made = argparse.ArgumentParser(add_help=False, **options)
    made.error = lambda message: refuse(doc)
    return made


def refuse(doc):
    print(doc, file=sys.stderr)
    sys.exit(2)
