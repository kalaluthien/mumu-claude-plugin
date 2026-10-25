"""book: the core of the paperwork book skill. const, dom -> plan -> build -> lint -> text, edit, demos, qa, figs, mutate; cli routes make-book.py's commands; api is what agents reads.

Figure scripts import `glob`, `Fig` and `fact` from here.
"""
import glob  # noqa: F401 (re-exported for figure scripts)

from .figs import Fig, fact  # noqa: F401
