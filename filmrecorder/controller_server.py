from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class ControllerServer:
    def __init__(self, command_sink: Callable[[dict], None], state_provider: Callable[[], dict], token: str = 'filmset'):
        self.command_sink = command_sink
        self.state_provider = state_provider
        self.token = token
        self.httpd = None
        self.thread = None

    def start(self, host='0.0.0.0', port=8765):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def _authorized(self):
                return self.headers.get('X-FilmRec-Token', '') == parent.token

            def _send(self, code: int, obj: dict):
                body = json.dumps(obj).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == '/health':
                    return self._send(200, {'ok': True})
                if not self._authorized():
                    return self._send(401, {'error': 'unauthorized'})
                if self.path == '/status':
                    return self._send(200, parent.state_provider())
                return self._send(404, {'error': 'not found'})

            def do_POST(self):
                if not self._authorized():
                    return self._send(401, {'error': 'unauthorized'})
                if self.path != '/command':
                    return self._send(404, {'error': 'not found'})
                length = int(self.headers.get('Content-Length', '0'))
                try:
                    payload = json.loads(self.rfile.read(length) or b'{}')
                    parent.command_sink(payload)
                    self._send(202, {'accepted': True})
                except Exception as exc:
                    self._send(400, {'error': str(exc)})

            def log_message(self, fmt, *args):
                pass

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
