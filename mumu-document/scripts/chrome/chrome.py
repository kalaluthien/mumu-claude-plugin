"""Render a page in headless Chrome through a frame script and read back what it wrote.

The frame is HTML whose script loads `location.hash` (the page's file url) into an iframe
and writes its result as JSON into `document.body.dataset.r`.
"""
import html
import json
import os
import re
import subprocess
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def available():
    return os.access(CHROME, os.X_OK)


def render(frame, page, *flags):
    """The JSON the frame wrote for `page`, or None when Chrome gave nothing back."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(frame)
    try:
        r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--allow-file-access-from-files", "--dump-dom",
                            *flags, "--virtual-time-budget=3000", f"file://{f.name}#file://{page}"],
                           capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(f.name)
    m = re.search(r'data-r="([^"]*)"', r.stdout)
    return json.loads(html.unescape(m.group(1))) if m else None
