#!/usr/bin/env python3
"""Replay the relay of `../relay_page.py`, `../relay_server.py` and `../relay-runtime.js` from a skill script of no skill, and system's connect command through a copy of the plugin.

usage: replay-relay-parts.py

relay parts: in a scratch folder a bare page and a stand-in skill script that connects the page and serves it through the lib modules;
`drive-relay-page.cjs` starts that script and, in a headless Chromium, comments on the page, sees the comment queued and one pending line,
writes the page file and acks the comment, and sees the open page reload with the queue empty.
system reach: on a copy of the plugin whose lib runtime ends with a marked comment, system's `connect-page.py` must write that comment into
a page, and no file under `skills/system/` may hold the runtime, the server or the connect code itself.
It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import pathlib
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = LIB.parent
BARE = '<!doctype html><html><body><p data-id="idea">An idea</p></body></html>\n'
STAND_IN = f'''import pathlib
import sys

sys.path.insert(0, {str(LIB)!r})
from relay_page import connect
from relay_server import serve

page = pathlib.Path(sys.argv[1]).resolve()
print(connect(page), page, flush=True)
sys.exit(serve(page, 0, 1.0))
'''
OWN = ("def connect(", "def serve(", "class Handler(", "window.recordChange = (")  # a line only the shared code itself holds


def relay_parts():
    """Each reason the stand-in script's relay loop failed."""
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        (folder / "page").mkdir()
        page, script = folder / "page" / "page.html", folder / "serve-page.py"
        page.write_text(BARE)
        script.write_text(STAND_IN)
        done = subprocess.run(["node", str(HERE / "drive-relay-page.cjs"), str(page), "idea", sys.executable, str(script), str(page)],
                              capture_output=True, text=True, timeout=120)
    said = (done.stdout.strip().splitlines() or [done.stderr.strip()])[-1]
    return [] if said == "PASS relay loop" else [said]


def system_reach():
    """Each reason system's connect command does not take its runtime from lib, or system keeps a copy of the shared code."""
    found = [f"{path.relative_to(PLUGIN)} holds `{mark}`" for path in sorted((PLUGIN / "skills" / "system").rglob("*")) if path.is_file()
             and path.suffix in (".py", ".js", ".cjs") for mark in OWN if mark in path.read_text(errors="replace")]
    with tempfile.TemporaryDirectory() as scratch:
        copied = pathlib.Path(scratch) / "paperwork"
        shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns("examples", "__pycache__"))
        runtime = copied / "lib" / "relay-runtime.js"
        if not runtime.is_file():
            return found + ["the plugin holds no lib/relay-runtime.js"]
        runtime.write_text(runtime.read_text().rstrip() + "\n// marked copy\n")
        page = pathlib.Path(scratch) / "page.html"
        page.write_text(BARE)
        done = subprocess.run([sys.executable, str(copied / "skills" / "system" / "scripts" / "connect-page.py"), str(page)], capture_output=True, text=True)
        if done.returncode or "// marked copy" not in page.read_text():
            found.append(f"connect-page.py on the copy wrote no marked runtime: {(done.stdout + done.stderr).strip()}")
    return found


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    for step, run in (("relay parts", relay_parts), ("system reach", system_reach)):
        reasons = run()
        failed = failed or bool(reasons)
        print(f"FAIL {step}: {'; '.join(reasons)}" if reasons else f"PASS {step}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
