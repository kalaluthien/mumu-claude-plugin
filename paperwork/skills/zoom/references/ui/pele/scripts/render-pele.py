#!/usr/bin/env python3
"""Draw the root level of a Schema document with pele: schema.json -> Mermaid -> SVG -> PNG.

Usage: render-pele.py <schema.json> <out.png>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Outside the repository so the install never lands in a commit.
CACHE = Path.home() / ".cache" / "zoom-render-pele"


def mermaid_id(raw):
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", raw)


def quote(text):
    return '"' + text.replace('"', "'") + '"'


def to_mermaid(level):
    """Calculation: a level's nodes and edges as a Mermaid flowchart."""
    lines = ["flowchart LR"]
    for node in level["nodes"]:
        lines.append(f'  {mermaid_id(node["id"])}[{quote(node["label"])}]')
    for edge in level["edges"]:
        label = edge.get("label")
        arrow = f"-->|{quote(label)}|" if label else "-->"
        lines.append(f'  {mermaid_id(edge["from"])} {arrow} {mermaid_id(edge["to"])}')
    return "\n".join(lines) + "\n"


def install():
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "package.json").write_text((HERE.parent / "assets" / "package.json").read_text())
    if not (CACHE / "node_modules" / "pele").exists():
        subprocess.run(["npm", "install", "--silent"], cwd=CACHE, check=True)


def find_chromium():
    found = sorted((Path.home() / "Library/Caches/ms-playwright").glob(
        "chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell"))
    return str(found[-1]) if found else ""


def main():
    schema, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    install()
    mmd = out.with_suffix(".mmd")
    mmd.write_text(to_mermaid(json.loads(schema.read_text())["level"]))
    # The script sits in CACHE so node resolves pele and playwright-core from its node_modules.
    runner = CACHE / "render-pele.mjs"
    runner.write_text((HERE / "render-pele.mjs").read_text())
    subprocess.run(["node", str(runner), str(mmd), str(out), find_chromium()], check=True)
    print(out)


main()
