#!/usr/bin/env python3
"""Draw the root level of a Schema document in tldraw offline: schema.json -> Mermaid -> shapes -> PNG.

Usage: render-tldraw.py <schema.json> <out.png>
Needs the tldraw offline app installed; the script opens it when it is not running.
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SUPPORT = Path.home() / "Library/Application Support/tldraw"


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


def server():
    """The app writes server.json on launch and removes it on a clean quit."""
    path = SUPPORT / "server.json"
    if not path.exists():
        subprocess.run(["open", "-a", "tldraw offline"], check=True)
        for _ in range(30):
            if path.exists():
                break
            time.sleep(1)
        else:
            sys.exit("tldraw offline did not start: no server.json")
    info = json.loads(path.read_text())
    return f'http://localhost:{info["port"]}', info["token"]


def call(base, token, path, body, as_text=False):
    data = body.encode() if as_text else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, headers={
        "authorization": f"Bearer {token}",
        "content-type": "text/plain" if as_text else "application/json"})
    answer = json.load(urllib.request.urlopen(request, timeout=120))
    if not answer.get("success"):
        sys.exit(f"{path} failed: {answer.get('error')}")
    return answer["result"]


def main():
    schema, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    mermaid = to_mermaid(json.loads(schema.read_text())["level"])
    base, token = server()
    # A new file per run: the owner's open documents stay untouched.
    folder = out.parent / f"{out.stem}-tldraw"
    folder.mkdir(parents=True, exist_ok=True)
    doc = call(base, token, "/api/docs/create", {
        "name": f"{out.stem}-{int(time.time())}", "directory": str(folder)})
    draw = f"await helpers.mermaid({json.dumps(mermaid)}); await helpers.saveDoc(); return editor.getCurrentPageShapes().length"
    shapes = call(base, token, f'/api/doc/{doc["id"]}/exec', draw, as_text=True)
    if not shapes:
        sys.exit("tldraw drew no shapes")
    shot = call(base, token, "/api/search", {
        "code": f'return await api.getScreenshot({json.dumps(doc["id"])}, {{ size: "large" }})'})
    # getScreenshot answers a JPEG; sips writes the PNG.
    subprocess.run(["sips", "-s", "format", "png", shot["filePath"], "--out", str(out)],
                   check=True, capture_output=True)
    print(out)


main()
