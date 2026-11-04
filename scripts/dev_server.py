"""Local preview of web/ without deploying: serves the files and forwards /api/* to the live API.

    python scripts/dev_server.py            # http://localhost:8088  (API from build/outputs.json)
    python scripts/dev_server.py --api https://xxxx.cloudfront.net --port 8088

Only for development. Uses the deployed backend, so chats count against its daily cap.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "build" / "outputs.json"


class Handler(SimpleHTTPRequestHandler):
    api_base = ""

    def _proxy(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(  # noqa: S310 (our own HTTPS endpoint)
            self.api_base + self.path,
            data=body,
            method=self.command,
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:  # noqa: S310
                status, data = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, data = exc.code, exc.read()
        except Exception as exc:  # network down: same shape as the API's own errors
            status, data = 502, json.dumps({"error": type(exc).__name__}).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def end_headers(self) -> None:
        self.send_header("cache-control", "no-store")
        super().end_headers()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--api", default=None, help="base URL of the deployed site (default: build/outputs.json)"
    )
    ap.add_argument("--port", type=int, default=8088)
    args = ap.parse_args()
    api = args.api or json.loads(OUTPUTS.read_text())["AlTiempoApp"]["SiteUrl"]
    Handler.api_base = api.rstrip("/")
    handler = partial(Handler, directory=str(ROOT / "web"))
    server = None
    for port in range(args.port, args.port + 20):  # busy port (another app)? use the next free one
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit(f"No free port between {args.port} and {args.port + 19}")
    print(
        f"Al Tiempo local preview: http://localhost:{port}  (API -> {Handler.api_base})", flush=True
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
