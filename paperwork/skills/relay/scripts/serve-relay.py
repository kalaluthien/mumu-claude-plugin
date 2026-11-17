#!/usr/bin/env python3
"""Queue the change events an open HTML page sends for a Claude Code session to apply, and tell the page to reload when its file changes.

usage: serve-relay.py <page.html> [--port <n>] [--quiet <seconds>]

It binds 127.0.0.1 behind a random token, `http://127.0.0.1:<port>/<token>/`, written to `url.txt` beside the page and
reused on a restart. Its first stdout line is `relay url: <url>`; once a change is queued and `--quiet` seconds
(default 3) pass with no newer one, it prints one `relay pending ...` line carrying the commands that pull and
ack the queue. It never writes the page: each version of it is copied, read only, into `history/`; events wait in
`changes/pending.jsonl` and acked ones move to `changes/applied.jsonl`."""
import datetime
import hashlib
import http.server
import json
import mimetypes
import os
import pathlib
import re
import secrets
import sys
import threading
import time

ANCHOR = re.compile(r"[\w.:-]{1,80}")
KINDS = ("comment", "data")
RECORDS = ("changes", "history", "url.txt")
LIMIT = 1_000_000
RUNTIME_END = b"<!-- /relay runtime -->"
HANDLED = ("do_GET", "do_POST", "log_message")  # http.server calls these by name


def main(args):
    if not args or args[0].startswith("-"):
        return usage()
    page = pathlib.Path(args[0]).resolve()
    port, quiet, rest = 0, 3.0, args[1:]
    while rest:
        flag, value = rest.pop(0), rest.pop(0) if rest else ""
        if flag == "--port" and value.isdigit():
            port = int(value)
        elif flag == "--quiet" and re.fullmatch(r"\d+(\.\d+)?", value):
            quiet = float(value)
        else:
            return usage()
    if not page.is_file():
        return usage()
    folder = page.parent
    changes, history = folder / "changes", folder / "history"
    for each in (changes, history):
        each.mkdir(exist_ok=True)
    pending_file, applied_file = changes / "pending.jsonl", changes / "applied.jsonl"
    saved = folder / "url.txt"
    token = secrets.token_urlsafe(16)
    try:  # a restart keeps the url an open page and a session already hold
        old = saved.read_text().strip().split("/")
        port, token = port or int(old[2].split(":")[1]), old[3]
    except (OSError, IndexError, ValueError):
        pass
    lock = threading.Lock()
    known = read(pending_file) + read(applied_file)
    state = {"digest": None, "queue": 0, "due": None,
             "next": max([0] + [each["id"] for each in known if isinstance(each.get("id"), int)]) + 1}

    def add(message):
        kind, target, payload = message.get("kind"), message.get("target"), message.get("payload")
        if kind not in KINDS or not isinstance(target, str) or not ANCHOR.fullmatch(target) or not isinstance(payload, dict):
            return 400, None
        text = payload.get("text")
        if kind == "comment" and not (isinstance(text, str) and text.strip() and len(text) <= 4000):
            return 400, None
        event = {"id": state["next"], "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
                 "kind": kind, "target": target, "payload": payload}
        state["next"] += 1
        write(pending_file, read(pending_file) + [event])
        state["queue"] += 1
        state["due"] = time.monotonic() + quiet
        return 202, {"id": event["id"], "ts": event["ts"]}

    def ack(message):
        ids = message.get("ids")
        if not isinstance(ids, list):
            return 400, None
        wanted = {str(each) for each in ids}
        pending = read(pending_file)
        done = [event for event in pending if str(event["id"]) in wanted]
        if done:
            write(applied_file, read(applied_file) + done)
            write(pending_file, [event for event in pending if str(event["id"]) not in wanted])
            state["queue"] += 1
        return 200, {"acked": len(done)}

    def keep():
        """Copy the page into history/ when its content is new, and note its digest for the reload stream."""
        body = page.read_bytes()
        digest = hashlib.sha256(body).hexdigest()[:12]
        if digest == state["digest"]:
            return
        versions = sorted(history.glob("*.html"))
        if not versions or not versions[-1].name.endswith(f"-{digest}.html"):
            copy = history / f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')}-{digest}.html"
            copy.write_bytes(body)
            copy.chmod(0o444)
        # a page cut off mid-write lacks the runtime's closing marker, and a reload into it would leave a page that never reloads again
        if RUNTIME_END in body:
            state["digest"] = digest

    def watch():
        seen = last = None
        while True:
            try:
                stat = page.stat()
                now = (stat.st_mtime_ns, stat.st_size)
                # a file still being written changes between two polls, so only one quiet for a whole poll is read
                if now == last and now != seen:
                    seen = now
                    keep()
                last = now
            except OSError:
                pass
            time.sleep(0.5)

    def announce():
        """Print one line per burst of changes, once the person has paused, so a session's Monitor wakes once, not per keystroke."""
        while True:
            time.sleep(0.1)
            with lock:
                if state["due"] is None or time.monotonic() < state["due"]:
                    continue
                state["due"] = None
                events = read(pending_file)
            if events:
                comments = sum(event["kind"] == "comment" for event in events)
                ack_body = '{"ids":[<id>,...]}'
                print(f"relay pending {len(events)}: {comments} comment, {len(events) - comments} data for {page}"
                      f" | pull: curl -s {url}api/changes"
                      f" | ack after editing the page: curl -s -X POST -H 'Origin: {origin}' -H 'Content-Type: application/json'"
                      f" -d '{ack_body}' {url}api/changes/ack", flush=True)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, body=b"", kind="text/plain"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def route(self):
            parts = self.path.split("?")[0].split("/")
            if len(parts) < 3 or not secrets.compare_digest(parts[1], token):
                return None
            return "/".join(parts[2:])

        def stream(self):
            digest, queue, beat = state["digest"], state["queue"], time.monotonic()  # before the page hears it is connected
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(b"retry: 1000\n: connected\n\n")
                self.wfile.flush()
                while True:
                    time.sleep(0.5)
                    out = b""
                    if state["digest"] != digest:
                        digest, out = state["digest"], out + b"event: reload\ndata: {}\n\n"
                    if state["queue"] != queue:
                        queue, out = state["queue"], out + b"event: changes\ndata: {}\n\n"
                    if not out and time.monotonic() - beat >= 15:
                        out = b": keep-alive\n\n"
                    if out:
                        self.wfile.write(out)
                        self.wfile.flush()
                        beat = time.monotonic()
            except OSError:
                pass

        def do_GET(self):
            route = self.route()
            if route == "":
                return self.reply(200, page.read_bytes(), "text/html; charset=utf-8")
            if route == "api/changes":
                with lock:
                    events = read(pending_file)
                return self.reply(200, json.dumps(events, ensure_ascii=False).encode(), "application/json")
            if route == "api/events":
                return self.stream()
            try:
                beside = (folder / route).resolve() if route else folder
                inside = beside.relative_to(folder).parts
                # the file system may match a name in another letter case, so compare the file reached, not its spelling
                if beside.is_file() and not any(part.startswith(".") for part in inside) and not any(
                        (folder / each).exists() and os.path.samefile(folder / each, folder / inside[0]) for each in RECORDS):
                    return self.reply(200, beside.read_bytes(), mimetypes.guess_type(beside.name)[0] or "application/octet-stream")
            except (ValueError, OSError):
                pass
            self.reply(404)

        def do_POST(self):
            actions = {"api/changes": add, "api/changes/ack": ack}
            route = self.route()
            if route not in actions:
                return self.reply(404)
            if self.headers.get("Origin") != origin:
                return self.reply(403)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json" or length > LIMIT:
                    raise ValueError("not a JSON post")
                message = json.loads(self.rfile.read(length), parse_constant=refuse)
                if not isinstance(message, dict):
                    raise ValueError("not an object")
            except ValueError:
                return self.reply(400)
            with lock:
                code, body = actions[route](message)
            self.reply(code, json.dumps(body).encode() if body else b"", "application/json")

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as error:
        print(f"relay cannot listen on 127.0.0.1:{port}: {error}", file=sys.stderr)
        return 1
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    url = f"{origin}/{token}/"
    saved.write_text(url + "\n")
    keep()
    for each in (watch, announce):
        threading.Thread(target=each, daemon=True).start()
    print(f"relay url: {url}", flush=True)
    server.serve_forever()


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []


def write(path, items):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items))
    os.replace(temporary, path)


def refuse(word):
    """Refuse NaN and Infinity, which Python reads and a browser's JSON.parse does not."""
    raise ValueError(f"{word} is not JSON")


def usage():
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
