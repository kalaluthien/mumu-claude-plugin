#!/usr/bin/env python3
"""book.py: the book-authoring CLI; commands live in scripts/bk (see bk/cli.py or --help).

Figure scripts: sys.path.insert(0, SKILL/scripts); from book import glob, Fig, fact
"""
import glob, os, sys  # noqa: F401 (glob is re-exported for figure scripts)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bk.figs import Fig, fact  # noqa: E402,F401
from bk.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
