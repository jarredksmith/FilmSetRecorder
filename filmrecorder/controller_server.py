from __future__ import annotations

import json
import logging
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

LOGGER = logging.getLogger("filmsetrecorder.remote")


class ControllerServer:
    def __init__(
        self,
        command_sink: Callable[[dict], None],
        state_provider: Callable[[], dict],
        token: str,
    ):
        self.command_sink = command_sink
        self.state_provider = state_provider
        self.token = str(token)
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None
        self._seen_ids: deque[str] = deque(maxlen=128)
        self._seen_lock = threading.Lock()

    def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "FilmSetRecorderRemote/0.2"

            def _authorized(self) -> bool:
                return self.headers.get("X-FilmRec-Token", "") == parent.token

            def _send(self, code: int, obj: dict) -> None:
                body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                path = self.path.split("?", 1)[0]
                if path == "/health":
                    return self._send(200, {"ok": True, "service": "FilmSetRecorder"})
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                if path == "/status":
                    return self._send(200, parent.state_provider())
                return self._send(404, {"error": "not found"})

            def do_POST(self) -> None:
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                path = self.path.split("?", 1)[0]
                if path != "/command":
                    return self._send(404, {"error": "not found"})
                try:
                    length = min(int(self.headers.get("Content-Length", "0")), 16384)
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(payload, dict):
                        raise ValueError("Command payload must be a JSON object.")
                    request_id = str(payload.get("request_id", "")).strip()
                    if request_id:
                        with parent._seen_lock:
                            if request_id in parent._seen_ids:
                                return self._send(200, {"accepted": True, "duplicate": True})
                            parent._seen_ids.append(request_id)
                    parent.command_sink(payload)
                    self._send(202, {"accepted": True})
                except Exception as exc:
                    self._send(400, {"error": str(exc)})

            def log_message(self, fmt, *args) -> None:
                return

        class RecorderHTTPServer(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self.httpd = RecorderHTTPServer((host, int(port)), Handler)
        self.port = int(self.httpd.server_address[1])
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="FilmRecRemote", daemon=True)
        self.thread.start()
        LOGGER.info("Remote control server started on %s:%s", host, self.port)

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.port = None
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        LOGGER.info("Remote control server stopped")
