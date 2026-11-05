"""Local preview of web/ without deploying: serves the files and forwards /api/* to the live API.

    python scripts/dev_server.py            # http://localhost:8088  (API from build/outputs.json)
    python scripts/dev_server.py --api https://xxxx.cloudfront.net --port 8088
    python scripts/dev_server.py --local    # chat runs the agent from THIS checkout (make local)

Only for development. Without --local it uses the deployed backend (chats count against its daily
cap). With --local, /api/chat and /api/warm call agent/app.py in this process (Bedrock with your
local credentials and .env), so you can test changes before deploying; voice, reminders and the
quiz still go to the deployed API. Local reminders are a dry run (no EventBridge schedule).
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "build" / "outputs.json"


LOCAL_ROUTES = ("/api/chat", "/api/warm")


class Handler(SimpleHTTPRequestHandler):
    api_base = ""
    local_invoke = None  # agent.app.invoke when --local

    def _local(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        body = body if isinstance(body, dict) else {}
        session_id = str(body.pop("session_id", "")) or None
        if self.path.startswith("/api/warm"):
            body["warmup"] = True
        result = Handler.local_invoke(body, SimpleNamespace(session_id=session_id))
        data = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
        if Handler.local_invoke and self.path.startswith(LOCAL_ROUTES):
            return self._local()
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
    ap.add_argument(
        "--local", action="store_true", help="run the chat with the agent code of this checkout"
    )
    args = ap.parse_args()
    if args.local:
        import sys

        sys.path.insert(0, str(ROOT))
        from agent.app import invoke

        Handler.local_invoke = staticmethod(invoke)
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
    chat = "LOCAL agent (this checkout)" if args.local else Handler.api_base
    print(
        f"Al Tiempo local preview: http://localhost:{port}  (chat -> {chat}; "
        f"voice/reminders -> {Handler.api_base})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
