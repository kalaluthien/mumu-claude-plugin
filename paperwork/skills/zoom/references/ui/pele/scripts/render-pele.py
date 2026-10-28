#!/usr/bin/env python3
"""Draw the root level of a Schema document with pele: schema.json -> Mermaid -> SVG -> PNG.

usage: render-pele.py <schema.json> <out.png>
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
# Outside the repository so the install never lands in a commit.
CACHE = pathlib.Path.home() / ".cache" / "zoom-render-pele"


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
    for name in ("package.json", "package-lock.json"):
        (CACHE / name).write_text((HERE.parent / "assets" / name).read_text())
    if not (CACHE / "node_modules" / "pele").exists():
        # The lock file pins every dependency by hash, and no install script of a package runs.
        subprocess.run(["npm", "ci", "--ignore-scripts", "--silent"], cwd=CACHE, check=True)


def find_chromium():
    found = sorted((pathlib.Path.home() / "Library/Caches/ms-playwright").glob(
        "chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell"))
    return str(found[-1]) if found else ""


def main(args):
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    schema, output_path = pathlib.Path(args[0]), pathlib.Path(args[1]).resolve()
    install()
    mermaid_file = output_path.with_suffix(".mmd")
    mermaid_file.write_text(to_mermaid(json.loads(schema.read_text())["level"]))
    # The script sits in CACHE so node resolves pele and playwright-core from its node_modules.
    runner = CACHE / "render-pele.mjs"
    runner.write_text((HERE / "render-pele.mjs").read_text())
    subprocess.run(["node", str(runner), str(mermaid_file), str(output_path), find_chromium()], check=True)
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
