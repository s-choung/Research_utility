#!/usr/bin/env python3
"""공고 모니터링 로컬 서버 — 숨기기 API 제공"""

import json
import signal
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SCRIPT_DIR = Path(__file__).resolve().parent
HIDDEN_FILE = SCRIPT_DIR / "hidden_posts.json"
PORT = 19823


def load_hidden() -> list[str]:
    if HIDDEN_FILE.exists():
        return json.loads(HIDDEN_FILE.read_text("utf-8"))
    return []


def save_hidden(ids: list[str]):
    HIDDEN_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2), "utf-8")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            # serve summary.html
            self.path = "/summary.html"
            return super().do_GET()

        if parsed.path == "/hide":
            params = parse_qs(parsed.query)
            post_id = params.get("id", [""])[0]
            if post_id:
                hidden = load_hidden()
                if post_id not in hidden:
                    hidden.append(post_id)
                    save_hidden(hidden)
            self._json_response({"ok": True, "hidden": len(load_hidden())})
            return

        if parsed.path == "/unhide":
            params = parse_qs(parsed.query)
            post_id = params.get("id", [""])[0]
            if post_id:
                hidden = load_hidden()
                if post_id in hidden:
                    hidden.remove(post_id)
                    save_hidden(hidden)
            self._json_response({"ok": True, "hidden": len(load_hidden())})
            return

        super().do_GET()

    def _json_response(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress logs


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    # 5분 후 자동 종료
    timer = threading.Timer(300, lambda: (server.shutdown()))
    timer.daemon = True
    timer.start()

    print(f"Server running on http://localhost:{PORT} (auto-stop in 5min)")
    server.serve_forever()


if __name__ == "__main__":
    main()
